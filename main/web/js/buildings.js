/* buildings.js - Buildings mode: export_descr_buildings.txt - levels, recruit
   pools, requires clauses, upgrades and cross-tree editing

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   Buildings mode - data/export_descr_buildings.txt

   A building "line" is an upgrade chain (Barracks -> Militia Barracks -> …).
   The grid lists lines; opening one gives a tab per level with its stats, its
   capabilities and, the point of the whole screen, its recruit pools: which
   units it trains, at what rate, for whom.

   Building art is per CULTURE, not per faction - data/ui/<culture>/buildings/
   #<culture>_<level>.tga is the small icon and #<culture>_<level>_constructed.tga
   the big one. A mod ships only what it changed, so anything it doesn't have
   falls back to unpacked vanilla art and then to a drawn placeholder; the badge
   on the picture says which you're looking at.
   ========================================================================= */

const BLD_SETTLE_LABEL={city:tt('buildings.city'),castle:tt('buildings.castle'),both:tt('buildings.city_castle')};

//: The four numbers of a `recruit_pool` line, explained on their ? markers.
const POOL_HELP={
  initial:tt('buildings.pool_help_initial'),
  per_turn:tt('buildings.pool_help_per_turn'),
  maximum:tt('buildings.pool_help_maximum'),
  experience:tt('buildings.pool_help_experience'),
};

/* ---- number boxes ----
   A number box is an ordinary input with ▲▼ beside it; the arrows only set
   .value and fire `input`, so the field's own handler stores the change exactly
   as typing would (and so undo records it as one step).

   `step` is how far one click moves the value, with one special case: 'turns'
   moves a recruit rate by one whole TURN rather than by a fraction. A rate of
   0.066667 is "a unit every 15 turns", and nobody thinks in the fraction - ▲
   there gives 1/14 = 0.071429, still "the number goes up". */
const numFmt=n=>String(+(+n).toFixed(6));
function numBox(attrs,value,step,after){
  return `<span class="numwrap"><input ${attrs} data-step="${esc(step)}"
      value="${esc(value)}" inputmode="decimal">
    <span class="spin"><button type="button" tabindex="-1" data-bump="1" title="${ttA('buildings.increase')}">▲</button
      ><button type="button" tabindex="-1" data-bump="-1" title="${ttA('buildings.decrease')}">▼</button></span>
    ${after||''}</span>`;
}
// Turns per unit, for a recruit pool's points-per-turn. 0 or nonsense = never.
function poolTurns(v){
  const n=parseFloat(v);
  if(!isFinite(n)||n<=0)return tt('buildings.never');
  const t=1/n;
  if(t<=1.02)return tt('buildings.every_turn');
  // 94b: a count, so each language's own plural (8.9 is "other" in most)
  return ttN('buildings.turns_count',t<10?+numFmt(t.toFixed(1)):Math.round(t));
}
/* A pool count of 1 and a pool count of 0 are different buildings, and the
   useful value between them is 0.99: the pool fills but never reaches a whole
   point, so the unit shows without ever becoming recruitable. Stepping straight
   from 1 to 0 meant typing it by hand every time. */
const POOL_EDGE=0.99;
function numBump(inp,dir){
  const step=inp.dataset.step||'1';
  const cur=parseFloat(inp.value);
  let next;
  if(step==='turns'){
    const turns=(isFinite(cur)&&cur>0)?Math.max(1,Math.round(1/cur)):1;
    next=1/Math.max(1,turns-dir);       // ▲ = one turn sooner = a bigger rate
  }else if(step==='pool'){
    const v=isFinite(cur)?cur:0;
    next=dir<0 ? (v>1?v-1:(v>POOL_EDGE?POOL_EDGE:0))
               : (v<POOL_EDGE?POOL_EDGE:(v<1?1:v+1));
  }else{
    next=(isFinite(cur)?cur:0)+dir*(parseFloat(step)||1);
    if(next<0)next=0;                   // no negative costs, pools or build times
  }
  inp.value=numFmt(next);
  inp.dispatchEvent(new Event('input',{bubbles:true}));
}
// Wire every ▲▼ under `root`, and keep any "= 15 turns" readout beside a rate
// box in step with what is typed into it.
function wireNumBoxes(root){
  root.querySelectorAll('.numwrap').forEach(w=>{
    const inp=w.querySelector('input'); if(!inp)return;
    const turns=w.querySelector('.turns');
    w.querySelectorAll('[data-bump]').forEach(btn=>{
      btn.onclick=e=>{e.preventDefault();numBump(inp,+btn.dataset.bump);};
    });
    // ↑/↓ in the box do what the arrows beside it do - including the 1 → 0.99 → 0
    // step on a pool count, which is the whole reason to reach for the key
    inp.addEventListener('keydown',e=>{
      const dir=e.key==='ArrowUp'?1:e.key==='ArrowDown'?-1:0;
      if(!dir)return;
      e.preventDefault(); numBump(inp,dir);
    });
    if(turns)inp.addEventListener('input',()=>{turns.textContent='= '+poolTurns(inp.value);});
  });
}

/* `anyCulture` is for screens that are not showing a culture at all - see
   `buildings.find_icon`. The building browser never passes it: a level the
   picked culture has no art for is a fact about that culture, and the grid
   says so. The unit editor's Recruitment tab does, because its rows come from
   every line in the mod and belong to no one culture. */
function bldIcon(level,kind,culture,anyCulture){
  return `/building_icon?mod=${enc(state.src)}&culture=${enc(culture||bldCultureNow())}`
       + `&level=${enc(level)}&kind=${kind||'small'}${anyCulture?'&any=1':''}`;
}
function bldCultureNow(){
  const b=state.bld; return (b&&b.culture)||'';
}
// One in-flight request per mod, shared by every caller. render() fires again on
// each keystroke and filter tick, and switching mod nulls state.bld mid-await -
// without this the second caller could resume before the first had assigned.
//
// The overview is also per CULTURE, because a building's name is: DaC names
// every one of its buildings per culture and leaves the shared key a
// placeholder, so the grid has to ask for the names of the culture on show.
let _bldLoading=null;
async function loadBuildings(force){
  const want=state.settings.bld_culture||'';
  if(state.bld&&state.bld.mod===state.src&&!force)return state.bld;
  if(_bldLoading&&_bldLoading.mod===state.src&&!force)return _bldLoading.p;
  // The unit editor's Recruitment tab asks for this with a dialog OVER `main`,
  // and a "reading…" left behind there is what you would be looking at the
  // moment the dialog closes. Only the screen that is actually waiting says so.
  if(!overlay.classList.contains('open'))
    main.innerHTML=`<div class="empty">${tt('common.reading')} `+esc(state.src)+`${tt('buildings.s_buildings')}</div>`;
  const mod=state.src;
  const p=(async()=>{
    let ov=await api.get('/api/buildings?mod='+enc(mod)+'&culture='+enc(want));
    // Which culture's art and names lead: whatever was picked last if this mod
    // has it, else the first culture folder that holds building art.
    const culture=(ov.cultures||[]).includes(want)?want:(ov.cultures||[])[0]||'';
    // the remembered culture is not one this mod has, so the names that came
    // back are the wrong culture's - ask again for the one actually on show
    if(culture!==want)ov=await api.get('/api/buildings?mod='+enc(mod)+'&culture='+enc(culture));
    const b={mod,ov,culture,line:null,d:null,work:null,lvl:0,plan:null,own:{},
             view:state.settings.bld_view==='grid'?'grid':'rows',
             poolFac:new Set(),fixOwnership:true,
             sel:{settlement:new Set(),religion:new Set(),faction:new Set()}};
    // the mod may have been switched away from while this was in flight
    if(state.src===mod)state.bld=b;
    return b;
  })();
  _bldLoading={mod,p};
  try{ return await p; }
  finally{ if(_bldLoading&&_bldLoading.p===p)_bldLoading=null; }
}
async function renderBuildings(){
  let b;
  try{ b=await loadBuildings(); }
  catch(e){ main.innerHTML=`<div class="empty">${tt('buildings.couldnt_read_the_buildings_of',{src:esc(state.src)})}<br>
    <span class="count">${esc(errText(e))}</span><br><br>
    <button class="primary" onclick="render()">${tt('common.retry')}</button></div>`; return; }
  // the picker moved on while we were loading - whoever it moved to will render
  if(!b||b.mod!==state.src||state.mode!=='buildings')return;
  const ov=b.ov;
  if(!ov.has_file){
    main.innerHTML=`<div class="empty">${tt('buildings.has_no_data_export_descr_buildings',{src:esc(state.src)})}</div>`;
    count.textContent=''; return;
  }
  bldBuildFilters();
  const lines=ov.lines.filter(bldMatches);
  count.textContent=`${lines.length}/${ov.lines.length}`;
  const head=`<div class="faction-head">
      <h2>${tt('buildings.buildings',{src:esc(state.src)})}</h2>
      ${tt('buildings.lines_and_levels',{lines:ttN('buildings.line_count',lines.length),levels:ttN('buildings.level_count',lines.reduce((n,l)=>n+l.level_count,0)),vanilla:ov.vanilla_ui?'':`<span class="n w-warn">${tt('buildings.no_unpacked_vanilla_ui_so_missing')}</span>`,religions:ov.religions_are_vanilla?`<span class="n w-warn"
        title="${ttA('buildings.this_mod_has_no_data_descr')}">${tt('buildings.using_vanillas_five_religions')}</span>`:''})}
          <button class="${bldBrowse()==='gallery'?'on':''}" onclick="bldSetBrowse('gallery')"
            title="${ttA('buildings.cards_with_each_lines_finished_art')}">${tt('buildings.gallery')}</button>
          <button class="${bldBrowse()==='tree'?'on':''}" onclick="bldSetBrowse('tree')"
            title="${ttA('buildings.one_row_per_line_its_levels')}">${tt('buildings.tree')}</button>
        </span>
        ${(ov.actions||{}).create?`<button onclick="bimOpen()"
          title="${ttA('buildings.bring_building_lines_in_from_another')}">${tt('buildings.from_another_mod')}</button>
        <button class="primary" onclick="bldNewTree()"
          title="${ttA('buildings.add_a_whole_new_building_line')}">${tt('buildings.new_building_tree')}</button>`:''}
      </span>
    </div>
    ${bldTreeChkHtml()}
    ${bldHidHtml()}`;
  if(!lines.length){
    main.innerHTML=`<section class="faction-group">${head}
      <div class="empty">${tt('buildings.no_buildings_match')}</div></section>`;
    return;
  }
  main.innerHTML=`<section class="faction-group">${head}${
    bldBrowse()==='tree'
      ? `<div class="btree">${lines.map(bldTreeRowHtml).join('')}</div>`
      : `<div class="bgrid">${lines.map(bldCardHtml).join('')}</div>`}</section>`;
  main.querySelectorAll('.bcard').forEach(c=>c.onclick=()=>openBuilding(c.dataset.line));
}
/* ---- gallery ⇄ tree ----
   Two ways of reading the same list, and which one is useful depends on what you
   came for. The gallery shows every line's finished picture, which is how you
   recognise a building you have seen in game; the tree shows the whole EDB at
   once - DaC's 136 lines and 499 levels fit on two screens - which is how you
   find the level a unit is trained from. The choice is remembered, because
   nobody wants to re-pick it every launch. */
const bldBrowse=()=>(state.settings.bld_browse==='tree'?'tree':'gallery');
function bldSetBrowse(v){
  state.settings.bld_browse=v; api.post('/api/settings',{bld_browse:v});
  render();
}
// which lines are unfolded, kept on the mod's state so it survives a re-render
// but not a mod switch
const bldOpenTrees=()=>{
  const b=state.bld; if(!b.open)b.open=new Set(); return b.open;
};
function bldTreeToggle(name){
  const open=bldOpenTrees();
  open.has(name)?open.delete(name):open.add(name);
  render();
}
function bldTreeRowHtml(l){
  const open=bldOpenTrees().has(l.name);
  const a=bldCardArt(l),top=l.top_level||l.levels[l.levels.length-1]||'';
  const bits=[BLD_SETTLE_LABEL[l.settlement]||l.settlement,
    ttN('buildings.level_count',l.level_count)];
  if(l.recruit_count)bits.push(ttN('buildings.count_of_units',l.recruit_count));
  if(l.religion)bits.push(esc(l.religion));
  if(l.convert_to)bits.push('↔ '+esc(l.convert_to));
  const warn=l.missing_units.length
    ? ` <span class="w-bad" title="${ttA('buildings.named_in_a_recruit_pool_but',{missing_units:esc(l.missing_units.join(', '))})}">${tt('buildings.unknown',{missing_units_n:l.missing_units.length})}</span>`:'';
  return `<div class="btrow${open?' open':''}" onclick="bldTreeToggle('${q1(esc(l.name))}')">
      <button class="btwist" tabindex="-1">${open?'▾':'▸'}</button>
      <img loading="lazy" onerror="iconRetry(this)" alt="" src="${bldIcon(top,'small',a.culture)}">
      <span class="antxt"><span class="nm">${esc(l.label)}</span>
        <span class="sub">${l.label===l.name?'':esc(l.name)+' · '}${
          bits.join(' · ')}${warn}</span></span>
      <button onclick="event.stopPropagation();openBuilding('${q1(esc(l.name))}')"
        title="${ttA('buildings.open_this_line_in_the_editor')}">${tt('buildings.open')}</button>
    </div>
    ${open?`<div class="btlevels">${l.levels.map((n,i)=>`
      <button class="btlv" onclick="openBuilding('${q1(esc(l.name))}',false,${i})"
        title="${ttA('buildings.open_2',{x:esc(n)})}">
        <img loading="lazy" onerror="iconRetry(this)" alt="" src="${bldIcon(n,'small',a.culture)}">
        <span class="t">${esc((l.level_labels||[])[i]||n)}</span>
        <span class="n">${esc(n)}</span></button>`).join('')}</div>`:''}`;
}
function bldCardHtml(l){
  // the last level is the finished building, so its constructed art is the one
  // that says what the line IS at a glance
  const top=l.top_level||l.levels[l.levels.length-1]||'';
  const a=bldCardArt(l);
  const tags=[`<span class="badge">${esc(BLD_SETTLE_LABEL[l.settlement]||l.settlement)}</span>`,
    `<span class="badge">${ttN('buildings.level_count',l.level_count)}</span>`];
  if(l.recruit_count)tags.push(`<span class="badge cls">${ttN('buildings.count_of_units',l.recruit_count)}</span>`);
  if(l.religion)tags.push(`<span class="badge merc">${esc(l.religion)}</span>`);
  if(l.missing_units.length)tags.push(`<span class="badge" style="color:var(--bad);border-color:var(--bad)"
      title="${ttA('buildings.named_in_a_recruit_pool_but',{missing_units:esc(l.missing_units.join(', '))})}"
      >${tt('buildings.unknown_2',{missing_units_n:l.missing_units.length})}</span>`);
  return `<div class="bcard" data-line="${esc(l.name)}">
    <div class="art"><img loading="lazy" onerror="iconRetry(this)" alt=""
        src="${bldIcon(top,'large',a.culture)}">
      ${bldArtBadge(a)}</div>
    <div class="bmeta"><div class="nm">${esc(l.label)}</div>
      <div class="sub">${esc(l.name)}</div>
      <div class="tags">${tags.join('')}</div></div></div>`;
}
// Where the card's picture comes from in the culture being shown: 'mod',
// 'vanilla' or '' for nothing at all. The overview says so per line, so the grid
// never has to ask the server about art it is already displaying.
function bldArtSource(l,culture){
  const a=(l.art||{})[culture||state.bld.culture]||{};
  return a.large||a.small||'';
}
// Most building lines are culture-specific, so with one culture picked the
// majority of the grid would be placeholders for buildings the mod HAS drawn -
// just for someone else. So a line with nothing in the chosen culture borrows
// the art of a culture that does have it, and the badge says whose.
function bldCardArt(l){
  const want=state.bld.culture;
  const own=bldArtSource(l,want);
  if(own)return {culture:want,source:own,borrowed:false};
  for(const c of Object.keys(l.art||{})){
    const s=bldArtSource(l,c);
    if(s)return {culture:c,source:s,borrowed:true};
  }
  return {culture:want,source:'',borrowed:false};
}
/* Whose art the pane is actually showing, said in words rather than as the bare
   token the server sends. "vanilla" on its own reads as a label, not as "this
   mod ships none and the game will fall back". */
function bldArtWhose(src){
  if(src==='mod')return `<span class="w-good">${tt('buildings.this_mods_own_art')}</span>`;
  if(src==='vanilla')return `<span class="w-warn" title="${ttA('buildings.this_mod_ships_no_file_at')}"
    >${tt('buildings.falling_back_to_the_vanilla_building')}</span>`;
  if(src==='vanilla*')return `<span class="w-warn" title="${ttA('buildings.no_vanilla_art_for_this_culture')}">${tt('buildings.falling_back_to_vanilla_art_from')}</span>`;
  return `<span class="w-warn">${tt('buildings.no_art_anywhere_showing_a_placeholder')}</span>`;
}
/* One of the two art panes in the building editor, with the swap on it.
   "Drop a .tga in to override it" is what `bldArtWhose` has been telling people
   to do by hand since the browser was written - this is that, done here: the ✎
   writes the mod's own copy at the path the fallback message names. */
function bldArtFig(size,level,caption,source){
  const url=bldIcon(level,size);
  return `<figure class="${size}">
    <div class="icowrap"><img onerror="iconRetry(this)" src="${url}"
      title="${ttA('common.replace_this_picture')}" onclick="imgPick('${q1(esc(url))}','bldRenderBodyNow')">
      ${imgEditBtn(url,'bldRenderBodyNow')}</div>
    <figcaption>${caption}<br>${bldArtWhose(source)}
      ${imgRow(url,'bldRenderBodyNow')}</figcaption></figure>`;
}
function bldArtBadge(a){
  if(a.borrowed)return `<span class="src vanilla"
    title="${ttA('buildings.this_mod_has_no_art_for',{culture:esc(state.bld.culture),culture2:esc(a.culture)})}"
    >${esc(a.culture)}</span>`;
  if(a.source==='vanilla')return `<span class="src vanilla"
    title="${ttA('buildings.borrowed_from_the_unpacked_vanilla_ui')}">${tt('buildings.vanilla')}</span>`;
  if(!a.source)return `<span class="src placeholder"
    title="${ttA('buildings.neither_this_mod_nor_the_unpacked')}">${tt('buildings.no_art')}</span>`;
  return '';
}
function bldMatches(l){
  const b=state.bld; if(!b)return true;
  const S=b.sel,qq=search.value.trim().toLowerCase();
  if(qq&&!(l.label.toLowerCase().includes(qq)||l.name.toLowerCase().includes(qq)
      ||l.levels.some(x=>x.toLowerCase().includes(qq))
      ||(l.level_labels||[]).some(x=>x.toLowerCase().includes(qq))))return false;
  if(S.settlement.size&&!S.settlement.has(l.settlement))return false;
  if(S.religion.size&&!S.religion.has(l.religion||'(none)'))return false;
  if(S.faction.size&&!l.factions.some(f=>S.faction.has(f)))return false;
  if(bldRecruitOnly.checked&&!l.recruit_count)return false;
  // "missing its own art" = the mod ships nothing for it in ANY culture
  if(bldMissingArt.checked&&Object.values(l.art||{}).some(a=>a.small==='mod'||a.large==='mod'))
    return false;
  return true;
}
let _bldFiltersFor='';
function bldBuildFilters(){
  const b=state.bld,ov=b.ov,key=b.mod+'|'+b.culture;
  if(_bldFiltersFor===key)return;                 // only rebuild when the mod changes
  _bldFiltersFor=key;
  bldCulture.innerHTML=(ov.cultures||[]).map(c=>
    `<option value="${esc(c)}" ${c===b.culture?'selected':''}>${esc(c)}</option>`).join('')
    ||`<option value="">${tt('buildings.no_culture_folders')}</option>`;
  bldCulture.onchange=()=>{bldSetCulture(bldCulture.value);};
  const religions=[...new Set(ov.lines.map(l=>l.religion||'(none)'))].sort();
  // rebuilt on a culture switch too, so the ticks come from the selection, not
  // from whatever the old boxes said
  bldReligionFilter.innerHTML=religions.map(r=>
    `<label class="opt"><input type="checkbox" value="${esc(r)}" ${b.sel.religion.has(r)?'checked':''}>${esc(r)}</label>`).join('');
  const factions=[...new Set(ov.lines.flatMap(l=>l.factions))]
    .sort((a,b2)=>bldFacLabel(a).localeCompare(bldFacLabel(b2)));
  bldFactionFilter.innerHTML=factions.map(f=>
    `<label class="opt"><input type="checkbox" value="${esc(f)}" ${b.sel.faction.has(f)?'checked':''}>${esc(bldFacLabel(f))}</label>`).join('')
    ||`<span class="count">${tt('common.none_2')}</span>`;
  // Which name leads: the Unit Editor's own setting, so the two screens agree.
  bldFacNames.value=facBy();
  bldFacNames.onchange=()=>{
    state.settings.faction_sort=bldFacNames.value;
    api.post('/api/settings',{faction_sort:bldFacNames.value});
    if(typeof facSort!=='undefined')facSort.value=bldFacNames.value;
    _bldFiltersFor=''; render();};
  const wire=(box,key2)=>box.querySelectorAll('input').forEach(cb=>cb.onchange=()=>{
    cb.checked?b.sel[key2].add(cb.value):b.sel[key2].delete(cb.value);
    if(key2==='faction'&&cb.checked&&bldFollowCulture(cb.value))return;
    render();});
  wire(bldReligionFilter,'religion'); wire(bldFactionFilter,'faction');
  document.querySelectorAll('.bldset').forEach(cb=>cb.onchange=()=>{
    const b2=state.bld; if(!b2)return;
    cb.checked?b2.sel.settlement.add(cb.value):b2.sel.settlement.delete(cb.value);
    render();});
  bldRecruitOnly.onchange=render;
  bldMissingArt.onchange=render;
  paintFilterFolds();
}
// A `requires factions { … }` clause names factions AND cultures; only the
// factions have an in-game name to show alongside the code.
function bldFacLabel(f){
  return state.factionNames[f]?facTwoNames(f,state.factionNames[f]):f;
}
/* ---------- the building editor ----------
   `atLevel` opens straight at one level rather than at the first: the tree list
   lists the levels, so clicking one has to land on it. `keepLevel` is the
   re-read after a Save, which stays where it was. */
async function openBuilding(name,keepLevel,atLevel){
  activity(tt('buildings.opened_building'),`${name} in ${state.src}`);
  const modal=document.getElementById('modal');
  modal.className='modal wide'; modal.innerHTML=`<h2>${tt('buildings.loading_building')}</h2>`;
  overlay.classList.add('open');
  let d;
  // the overview holds the culture list and the capability vocabulary the editor
  // needs; a save or a mod switch can leave it not yet loaded
  try{ await loadBuildings(); }
  catch(e){ modal.innerHTML=`<h2>${tt('buildings.building')}</h2><div class="mbody w-bad">${esc(errText(e))}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  try{ d=await api.get(`/api/building?mod=${enc(state.src)}&line=${enc(name)}`
                       +`&culture=${enc((state.bld&&state.bld.culture)||'')}`); }
  catch(e){ modal.innerHTML=`<h2>${tt('buildings.building')}</h2><div class="mbody w-bad">${esc(errText(e))}</div>
    <div class="foot"><button onclick="closeModal()">${tt('common.close')}</button></div>`; return; }
  const b=state.bld;
  b.line=name; b.d=d; b.plan=null; b.locSel=null;
  if(typeof atLevel==='number')b.lvl=Math.max(0,Math.min(atLevel,d.levels.length-1));
  else if(!keepLevel)b.lvl=0;
  // a different line (or a re-read after saving) means a different block of text
  cvDrop(b.cv); b.cv=null; cvDrop(b.cvKept); b.cvKept=null;
  // The working copy the form edits. Everything is sent on save and the server
  // skips whatever still matches the file, so the page never has to diff.
  // `locAll` is every culture's name/description keyed by culture ('' = the
  // shared key), so the culture picker never has to go back to the server.
  b.work=bldWorkFrom(d);
  b.orig=JSON.stringify(b.work);
  b.checks=null;
  // A different building starts filtered to the factions ticked in the browser,
  // because those are the ones you were looking for. A re-read after Save keeps
  // whatever the editor's own list says now.
  if(!keepLevel)b.poolFac=new Set(b.sel.faction);
  bldLoadChecks();
  b.own=b.own||{};                        // unit type -> ownership check result
  undoReset();
  // a re-read after Save keeps the level, so it keeps where you were scrolled
  // too; opening a different building starts at the top
  if(!keepLevel)resetPlace();
  renderBuildingEditor();
  // the code pane is remembered across records and modules; fetched after the
  // first paint so it never delays the dialog
  if(state.settings.code_view){
    b.cv=cvCreate(bldCvHost());
    cvLoad(b.cv).then(()=>{
      if(state.bld!==b||!b.cv)return;
      bldCvAdoptLoad(b.cv);
      renderBuildingEditor();
    });
  }
}
/* ---- which of a level's per-culture names is the one on show ----
   The same fallback the server uses (buildings._best_loc), redone here so the
   editor stays live when the culture picker moves: the culture's own key wins,
   then the shared key, then whichever culture DOES have text - a shared key
   whose value is just the key itself is a placeholder, not a name. */
function bldLocPlaceholder(rec){
  const n=((rec&&rec.name)||'').trim();
  return !n||n===(rec&&rec.key);
}
function bldLocCulture(lv,culture){
  const all=lv.locAll||{};
  const order=[culture,''].filter(c=>c in all)
    .concat(Object.keys(all).filter(c=>c&&c!==culture));
  for(const c of order) if(!bldLocPlaceholder(all[c]))return c;
  return culture in all?culture:'';
}
function bldLevelLabel(i){
  const b=state.bld, lv=b.work&&b.work.levels[i];
  if(!lv)return (b.d.levels[i]||{}).label||'';
  const rec=(lv.locAll||{})[bldLocCulture(lv,b.culture)]||{};
  return ((rec.name||'').trim())||lv.name;
}
// `conds` is the structured form of `requires`; `condEdited` says whether it has
// been touched. Only a touched clause is sent back as structure - an untouched
// one goes back as its original text, so the server never re-emits (and quietly
// tidies) a clause nobody edited.
/* The working copy the form edits, built from a /api/building detail payload.
   Everything is sent on save and the server skips whatever still matches the
   file, so the page never has to diff. `locAll` is every culture's
   name/description keyed by culture ('' = the shared key), so the culture picker
   never has to go back to the server.

   Its own function because Code View rebuilds it too: re-reading hand-edited
   text hands back a detail payload of exactly this shape, and the boxes have to
   come from that rather than from the file. */
function bldWorkFrom(d){
  const work={levels:d.levels.map(lv=>({
      name:lv.name, settlement:lv.settlement, requires:lv.requires,
      conds:JSON.parse(JSON.stringify(lv.conditions||[])), condEdited:false,
      scalars:Object.assign({},lv.scalars), upgrades:lv.upgrades.slice(),
      // the same list as name + conditions, so an upgrade's own clause can be
      // edited with the same picker as everything else. The strings above stay
      // the thing a save sends; these write back into them.
      upgConds:(lv.upgrade_paths||[]).map(u=>JSON.parse(JSON.stringify(u.conditions||[]))),
      locAll:JSON.parse(JSON.stringify(lv.loc_all||{'':Object.assign({present:true},lv.loc)})),
      caps:lv.capabilities.map(c=>bldCapCopy(c,false)),
      fcaps:lv.faction_capabilities.map(c=>bldCapCopy(c,true))}))};
  // Edits staged against OTHER building lines - the castle twin of this one, or
  // every tree that trains some unit. Kept inside `work` so dirty-tracking, undo
  // and Save pick them up with no special case: {line: {level: [rows]}}.
  work.also={};
  return work;
}
function bldCapCopy(c,faction){
  return {line:c.line,keyword:c.keyword,args:c.args,requires:c.requires,
          conds:JSON.parse(JSON.stringify(c.conditions||[])),condEdited:false,
          bonus:c.bonus,value:c.value,pool:c.pool?Object.assign({},c.pool):null,
          comment:c.comment,faction:faction,del:false};
}
function bldDirty(){
  const b=state.bld;
  return !!(b&&b.work&&(JSON.stringify(b.work)!==b.orig||bldCvEdited()));
}

/* ======================= CODE VIEW on the building editor =================
   The same widget the unit editor uses (web/js/codeview.js), pointed at the
   `edb` kind: the whole `building … { … }` block beside the form, hover-linked
   both ways, and hand-editable.

   A building line is a tree, not a field list, so re-reading hand-edited text
   hands back a whole detail payload and the form is rebuilt from it. And once
   the pane has done that, the save must go through the text FOREVER after -
   `bldCvOwns` - because the capability rows now carry line numbers relative to
   the pane's text rather than to the file, and planning those against the whole
   EDB would edit the wrong lines. */
const bldCvEdited=()=>{const cv=state.bld&&state.bld.cv;
  return !!(cv&&cv.loaded&&cv.base!==cv.pristine);};
// The pane that owns the text, whether it is on screen or not (see bldCvToggle).
const bldCvOf=()=>state.bld&&(state.bld.cv||state.bld.cvKept)||null;
const bldCvOwns=()=>{const cv=bldCvOf(); return !!(cv&&cv.owns);};
function bldCvBlocked(){
  const cv=bldCvOf();
  if(!cv||!cv.err)return '';
  return tt('buildings.code_view_cant_be_read',{error:cv.err});
}
function bldCvToggleHtml(){
  return `<button class="${state.bld.cv?'on':''}" title="${ttA('buildings.show_this_building_line_exactly_as')}"
    onclick="bldCvToggle()">${tt('common.code_view')}</button>`;
}
/* Hiding the pane must not forget its text. Once it owns the record the rows
   count their lines from that text, and a save without it planned those small
   numbers against the whole EDB: every row came back "capability line 8 is no
   longer there - skipped" and the edits to them were dropped. So a pane that
   owns the text is only put away (`cvKept`), saves keep going through it, and
   showing the pane again brings the same one back, redrawn from the boxes. */
async function bldCvToggle(){
  const b=state.bld;
  if(b.cv){
    if(b.cv.owns)b.cvKept=b.cv; else cvDrop(b.cv);
    b.cv=null; state.settings.code_view=false;
    api.post('/api/settings',{code_view:false}); renderBuildingEditor(); return;}
  state.settings.code_view=true; api.post('/api/settings',{code_view:true});
  if(b.cvKept){
    b.cv=b.cvKept; b.cvKept=null;
    renderBuildingEditor(); cvRender(b.cv);
    return;
  }
  b.cv=cvCreate(bldCvHost());
  renderBuildingEditor();
  await cvLoad(b.cv);
  if(state.bld!==b||!b.cv)return;
  bldCvAdoptLoad(b.cv);
  renderBuildingEditor();
}
function bldCvHost(){
  const b=state.bld;
  return {kind:'edb', mod:b.mod, id:b.line,
    where:'data/export_descr_buildings.txt',
    culture:()=>state.bld.culture||'',
    edits:()=>bldPayload(),
    adopt:cv=>{const s=state.bld;
      if(!cv.detail)return;
      s.d=cv.detail;
      // the level on screen may have been renamed or removed by the typing
      s.work=bldWorkFrom(cv.detail);
      s.lvl=Math.min(s.lvl,Math.max(0,s.work.levels.length-1));
      s.orig=JSON.stringify(s.work);},
    refreshGui:()=>bldCvRefresh(),
    label:bldCvLabel, find:bldCvFind};
}
/* The form is rebuilt from the pane the moment the pane arrives, before anything
   has been typed. That is not busywork: a capability row carries the LINE it sits
   on, and /api/building counts those from the top of the 30 000-line EDB while the
   pane counts them from the top of the block. Two conventions on one screen is a
   bug waiting for the first capability edit, so the pane's parse becomes the only
   one - and from then on the save goes through the pane's text (`owns`), which is
   the only text those numbers mean anything against.

   Box edits made while the pane was still loading are left alone; the pane simply
   doesn't take over in that case. */
function bldCvAdoptLoad(cv){
  const b=state.bld;
  if(!b||!cv||!cv.detail||cv.err)return;
  if(JSON.stringify(b.work)!==b.orig)return;
  b.d=cv.detail;
  b.work=bldWorkFrom(cv.detail);
  b.lvl=Math.min(b.lvl,Math.max(0,b.work.levels.length-1));
  b.orig=JSON.stringify(b.work);
  cv.owns=true;
}
// A redraw of the form only - never of the pane, which has the caret in it.
function bldCvRefresh(){
  const b=state.bld;
  if(!b||!b.work)return;
  const lv=b.work.levels[b.lvl],orig=b.d.levels[b.lvl];
  if(!lv||!orig)return;
  bldRenderBody(lv,orig);
  cvBindHover(b.cv,document.getElementById('bldGui'));
  paintDirty();
}
/* Which span the hovered element belongs to. The form's rows are `data-scalar`,
   `data-settlement` and `data-cap` - adding a second set of attributes to a
   three-thousand-line file would be churn, so the mapping lives here instead
   (codeview.js takes `label`/`find` from the host for exactly this). */
function bldCvLabel(el){
  const b=state.bld;
  if(!b||!b.work||!el||!el.closest)return '';
  const lv=b.work.levels[b.lvl]; if(!lv)return '';
  const key=tt('buildings.level_key',{name:lv.name});
  const cap=el.closest('[data-cap]');
  if(cap){
    const row=bldCapList()[+cap.dataset.cap];
    return (row&&bldCapPosLabel(lv,row))||key;
  }
  let f=el.closest('[data-scalar],[data-settlement]');
  // hovering the words beside a box counts as hovering the box
  if(!f&&el.nextElementSibling&&el.nextElementSibling.matches
     &&el.nextElementSibling.matches('[data-scalar],[data-settlement]'))
    f=el.nextElementSibling;
  if(f)return f.hasAttribute('data-settlement')?key+':header'
       :key+':'+(f.dataset.scalar||'');
  if(el.closest('.clausebar'))return key+':header';
  if(el.closest('#bldUpg'))return key+':upgrades';
  // anywhere else in the form: light the level this form IS
  return el.closest('#bldBody')?key:'';
}
/* A row's span, by the POSITION it is written at: `level:X:cap#N`, which the
   server puts on the Nth capability line of the text the pane shows. It used
   to be `capline#<file line>`, and that was right while a row could never
   move - since Phase 51 the list's order is the written order, so a moved row
   sits on a different line of the re-rendered text than the one it came from,
   and the line number lit its old neighbour. The position is right either
   way, and it gives a freshly added row a span too. A deleted row is not
   written, so it has none. */
function bldCapPosLabel(lv,row){
  if(!row||row.del)return '';
  const n=(row.faction?lv.fcaps:lv.caps).filter(c=>!c.del).indexOf(row)+1;
  return n?tt('buildings.level_3',{name:lv.name,x:row.faction?'fcap':'cap',x2:n}):'';
}
function bldCvFind(label){
  const b=state.bld;
  if(!b||!b.work)return [];
  const lv=b.work.levels[b.lvl]; if(!lv)return [];
  const m=/^level:(.+):(f?cap)#(\d+)$/.exec(label);
  if(m){
    if(m[1]!==lv.name)return [];
    const row=(m[2]==='fcap'?lv.fcaps:lv.caps).filter(c=>!c.del)[+m[3]-1];
    const i=row?bldCapList().indexOf(row):-1;
    const el=i<0?null:document.querySelector(`#bldBody [data-cap="${i}"]`);
    return el?[el]:[];
  }
  // the same line under its file-line name: the position above already says
  // it, and survives a move where this does not
  if(/^capline#/.test(label))return [];
  const pre=tt('buildings.level_key',{name:lv.name});
  if(label===pre+':header')
    return [...document.querySelectorAll('#bldBody [data-settlement],#bldBody .clausebar')];
  if(label===pre+':upgrades'){const u=document.getElementById('bldUpg');return u?[u]:[];}
  if(label.startsWith(pre+':')){
    const el=document.querySelector(
      `#bldBody [data-scalar="${cssq(label.slice(pre.length+1))}"]`);
    return el?[el]:[];
  }
  return [];
}
function bldLevelDirty(i){
  const b=state.bld;
  if(!b||!b.orig)return false;
  // 94a: the original is parsed once per `b.orig`, not once per call - opening
  // the editor asks this of every level, and each call parsed the whole 5 MB
  if(b._origFor!==b.orig){
    b._origFor=b.orig;
    b._origLv=JSON.parse(b.orig).levels.map(l=>JSON.stringify(l));
  }
  return JSON.stringify(b.work.levels[i])!==b._origLv[i];
}
function renderBuildingEditor(){
  const b=state.bld,d=b.d;
  const lv=b.work.levels[b.lvl],orig=d.levels[b.lvl];
  document.getElementById('modal').innerHTML=`
    <h2>${tt('buildings.building_line')} <span class="pill">${esc(b.mod)}</span></h2>
    <div class="ehead">
      <img style="width:74px;height:60px" onerror="iconRetry(this)"
        src="${bldIcon(d.levels[d.levels.length-1].name,'small')}">
      <div><div class="nm">${esc(d.label)}</div>
        <div class="count"><code>${esc(d.name)}</code> ${ttN('buildings.settlement_levels',d.levels.length,{settlement:esc(BLD_SETTLE_LABEL[d.settlement]||d.settlement),convert_to:d.convert_to?` ${tt('buildings.converts_to_name',{name:esc(d.convert_to)})}`:'',religion:d.religion?` ${tt('buildings.religion_name',{name:esc(d.religion)})}`:''})}</div>
        <div class="count">${tt('buildings.defined_in_data_export_descr_buildings',{plugins:d.plugins.length?tt('buildings.plugin_s',{plugins_n:d.plugins.length,x:esc(d.plugins.map(p=>p.name).join(', '))}):''})}</div></div>
      <span id="bldVarBtn">${bldVarBtnHtml()}</span>
    </div>
    <div class="lvstrip">${d.levels.map((l,i)=>`
      <div class="lvchip ${i===b.lvl?'on':''} ${bldLevelDirty(i)?'dirty':''}" onclick="bldPickLevel(${i})">
        <img loading="lazy" onerror="iconRetry(this)" src="${bldIcon(l.name,'small')}" alt="">
        <div class="t" title="${esc(bldLevelLabel(i))} (${esc(l.name)})">${esc(bldLevelLabel(i))}</div>
        <div class="n">${tt('buildings.units',{n:l.capabilities.filter(c=>c.pool).length})}</div>
      </div>`).join('')}</div>
    <div class="cvsplit${b.cv?'':' off'}" style="padding:0 14px">
      <div id="bldGui"><div class="mbody" id="bldBody" style="padding:0"></div></div>
      ${b.cv?`<div id="bldCodeCol" style="padding-top:12px">${cvHtml(b.cv)}</div>`:''}
    </div>
    <div class="foot">
      <span class="count" id="bldDirtyNote"></span>
      ${tt('buildings.ctrl_z_undo_ctrl_y_redo',{bldCvToggleHtml:bldCvToggleHtml()})}
      <label class="chk" style="margin-right:auto" title="${ttA('buildings.a_recruit_pool_can_name_a')}">
        <input type="checkbox" id="bldFixOwn" ${b.fixOwnership!==false?'checked':''}
          onchange="state.bld.fixOwnership=this.checked;bldDirtyNote()">
        ${tt('buildings.fix_unit_ownership_to_match')}</label>
      ${cleanerBoxHtml('building')}
      <button onclick="bldClose()">${tt('common.close')}</button>
      <button onclick="bldPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="bldSave()">${tt('common.save_changes')}</button>
    </div>`;
  bldRenderBody(lv,orig);
  if(b.cv){cvWire(b.cv); cvBindHover(b.cv,document.getElementById('bldGui'));}
}
/* The way into the city/castle comparison, big and top right where the thing
   it compares is named. The twin is worked out server-side and arrives with the
   checks, so the button knows whether there is anything on the other side before
   it is pressed: a line buildable in both settlement types has no other half,
   and the button says so instead of opening an empty panel. */
function bldVarBtnHtml(){
  const b=state.bld,twin=bldTwin();
  if(!twin)
    return `<button class="vcbtn" disabled title="${ttA('buildings.a_city_castle_pair_is_matched')}">${tt('buildings.no_city_castle_twin')}</button>`;
  const ck=b.checks||{};
  const gaps=(ck.mirror||[]).reduce((n,m)=>n+m.only_here.length+m.only_there.length,0);
  return `<button class="vcbtn primary" onclick="bldCompareVariants()"
    title="${ttA('buildings.put_this_building_beside_its_half',{settlement:esc(b.d.settlement==='city'?'castle':'city')})}">
    ${tt('buildings.compare_city_castle',{gaps:gaps?` <span class="badge warn">${gaps}</span>`:''})}</button>`;
}
function bldPickLevel(i){
  const b=state.bld; b.lvl=i; b.plan=null;
  // the ticks belong to the level they were made on - every row here is a
  // different object, and carrying a stale selection across only confuses
  if(b.bulk)b.bulk.sel.clear();
  renderBuildingEditor();
}
function bldClose(){
  if(bldDirty()&&!confirm(tt('buildings.close_without_saving_your_building_changes')))return;
  cvDrop(state.bld.cv); state.bld.cv=null; cvDrop(state.bld.cvKept); state.bld.cvKept=null;
  state.bld.line=null; state.bld.d=null; state.bld.work=null;
  closeModal();
}
function bldRenderBody(lv,orig){
  const b=state.bld,ov=b.ov;
  const body=document.getElementById('bldBody');
  /* The form is not always the thing in the dialog. Every panel that takes the
     modal over - Add units, the per-unit comparison, the city/castle comparison
     - leaves `#bldBody` out of the document, and a repaint aimed at it then
     threw on a null. That throw came out of an onclick, so it killed the click
     that caused it and everything after it: the page stopped responding, which
     is what "the tool crashed" looks like from the outside.

     Every caller is a change to the working copy, and the working copy is what
     the form is rebuilt from when the panel closes. So there is nothing to do
     here, and doing nothing is correct rather than merely safe. */
  if(!body)return;
  const scroll=body.scrollTop;
  // The pool and capability lists are scrollers of their OWN inside the body, so
  // putting the body back where it was is not enough: ticking a unit two hundred
  // rows down redrew the list and threw you back to the top of it.
  const scrollOf=id=>{const el=document.getElementById(id);return el?el.scrollTop:0;};
  const inner=[['bldPools',scrollOf('bldPools')],['bldCaps',scrollOf('bldCaps')]];
  const art=orig.art[b.culture]||{};
  const sel=(key,list,cur,blank)=>`<select data-scalar="${key}">
      ${blank?`<option value="">${esc(blank)}</option>`:''}
      ${list.map(v=>`<option value="${esc(v)}" ${v===cur?'selected':''}>${esc(v)}</option>`).join('')}
      ${cur&&!list.includes(cur)?`<option value="${esc(cur)}" selected>${esc(cur)} (custom)</option>`:''}
    </select>`;
  const pools=[...lv.caps,...lv.fcaps].filter(c=>c.pool);
  const plain=[...lv.caps,...lv.fcaps].filter(c=>!c.pool);
  const shown=pools.filter(bldPoolMatches);
  body.innerHTML=`
    <div class="bsec"><h4>${tt('buildings.art_culture',{culture:esc(b.culture||'none')})}</h4>
      <div class="bart">
        ${bldArtFig('small',orig.name,tt('buildings.tga',{culture:esc(b.culture),name:esc(orig.name)}),art.small)}
        ${bldArtFig('large',orig.name,
          tt('buildings.constructed_tga',{culture:esc(b.culture),name:esc(orig.name)}),art.large)}
        <div style="flex:1;min-width:180px">
          <div class="bnote">${tt('buildings.cultures_with_art_for_this_level')}</div>
          <div class="tags" style="margin-top:5px">${Object.keys(orig.art).length
            ? Object.keys(orig.art).map(c=>`<span class="badge ${c===b.culture?'cls':''}"
                style="cursor:pointer" onclick="bldSetCulture('${q1(esc(c))}')">${esc(c)}</span>`).join('')
            : `<span class="count">${tt('buildings.none_every_culture_falls_back_to')}</span>`}</div>
        </div>
      </div></div>

    ${bldLocSection(lv,orig)}

    <div class="bsec"><h4>${tt('buildings.stats')}</h4>
      <div class="brow">${tt('buildings.cost_turns_to_build',{x:qm(tt('buildings.what_the_settlement_pays_to_put'),tt('common.cost')),x2:numBox('data-scalar="cost"',lv.scalars.cost||'','100'),x3:qm(tt('buildings.how_many_turns_construction_takes_once'),tt('buildings.turns_to_build')),x4:numBox('data-scalar="construction"',lv.scalars.construction||'','1')})}</div>
      <div class="brow">${tt('buildings.material_convert_to',{qm:qm(tt('buildings.which_building_model_the_settlement_shows'),tt('buildings.material')),x:sel('material',ov.materials,lv.scalars.material||'','(unset)'),qm2:qm(tt('buildings.index_0_based_of_the_level'),tt('buildings.convert_to')),x2:numBox('data-scalar="convert_to"',lv.scalars.convert_to||'','1')})}</div>
      <div class="brow">${tt('buildings.settlement_min_max',{qm:qm(tt('buildings.the_smallest_settlement_size_that_may'),tt('buildings.settlement_min')),x:sel('settlement_min',ov.settlement_levels,lv.scalars.settlement_min||'','(unset)'),qm2:qm(tt('buildings.the_largest_settlement_size_that_may'),tt('buildings.settlement_max')),x2:sel('settlement_max',ov.settlement_levels,lv.scalars.settlement_max||'','(none)')})}</div>
      <div class="brow"><span class="k">${tt('buildings.buildable_in',{qm:qm(tt('buildings.whether_this_level_belongs_to_cities'),tt('buildings.buildable_in_2'))})}</span>
        <select data-settlement>
          <option value="" ${lv.settlement===''?'selected':''}>${tt('buildings.city_and_castle')}</option>
          <option value="city" ${lv.settlement==='city'?'selected':''}>${tt('buildings.city_only')}</option>
          <option value="castle" ${lv.settlement==='castle'?'selected':''}>${tt('buildings.castle_only')}</option>
        </select></div>
      <div class="brow"><span class="k">${tt('buildings.requires',{qm:qm(tt('buildings.everything_that_has_to_be_true'),tt('buildings.requires_2'))})}</span>
        <div class="clausebar">
          <div class="sum">${bldClauseSummary(lv.conds)}</div>
          <button class="reqbtn" onclick="bldEditClause('level')">${tt('buildings.edit_requirements')}</button>
        </div></div>
      ${bldRequiresHelp()}</div>

    ${bldUpgradesSection(lv,orig)}

    <div class="bsec ${foldCls('bld.recruit')}" data-fold="bld.recruit"><h4>${tt('buildings.recruitment_of',{shown_n:shown.length,n:pools.filter(p=>!p.del).length,x:bldPoolFilterHtml(pools)})}
        <div class="viewtoggle" style="margin-left:auto">
          <button class="${b.view!=='grid'?'on':''}" onclick="bldSetView('rows')">${tt('buildings.rows')}</button>
          <button class="${b.view==='grid'?'on':''}" onclick="bldSetView('grid')">${tt('buildings.grid')}</button>
        </div>
        <button style="margin-left:0" class="${bldBulkOn()?'on':''}" onclick="bldBulkToggle()"
          title="${ttA('buildings.tick_several_units_and_give_them')}"
          >${tt('buildings.bulk_edit')}</button>
        <button class="primary" onclick="bldAddPoolDialog()">${tt('buildings.add_unit')}</button></h4>
      ${bldBulkBar(shown)}
      ${bldPressureHtml(lv)}
      ${b.view==='grid'
        ? `<div class="ugrid" id="bldPools">${shown.length?shown.map(bldPoolCard).join('')
            :`<span class="count">${tt('common.nothing_matches')}</span>`}</div>`
        : `<div class="poollist" id="bldPools">${shown.length?shown.map(bldPoolRow).join('')
            :'<div class="poolrow"><span class="count">'
             +(pools.length?tt('buildings.nothing_matches_this_filter'):tt('buildings.this_level_trains_nothing'))
             +'</span></div>'}</div>`}</div>

    <div class="bsec ${foldCls('bld.caps')}" data-fold="bld.caps"><h4>${tt('buildings.other_capabilities')} <span class="n">${plain.filter(c=>!c.del).length}</span>
        <button onclick="bldAddCap()">${tt('buildings.add_capability')}</button></h4>
      <div class="caplist" id="bldCaps">${plain.length?plain.map(bldCapRow).join('')
        :`<div class="caprow"><span class="count">${tt('common.none_3')}</span></div>`}</div>
      ${lv.fcaps.length?`<div class="bnote">${tt('buildings.rows_marked_faction_live_in_this')} `
        +`${tt('buildings.faction_capability_block_so_they_apply')}</div>`:''}</div>

    ${bldChecksHtml()}
    ${bldAlsoHtml()}

    <div id="bldPlan"></div>`;
  if(b.plan)document.getElementById('bldPlan').innerHTML=bldPlanHtml(b.plan,b.planStale);
  bldWire();
  if(body&&scroll)body.scrollTop=scroll;
  inner.forEach(([id,top])=>{
    const el=document.getElementById(id); if(el&&top)el.scrollTop=top;});
  paintDirty();
}
/* ---- name & description, per culture ----
   One level can be called something different for every culture - Warg Breeder
   for the orcs, Stables for everyone else - and DaC does exactly that for its
   whole EDB, leaving the shared key a "DO NOT TRANSLATE" placeholder. So the
   editor picks a culture the way the game does, and writing to one culture
   leaves the others alone. */
function bldLocSel(){
  const b=state.bld,lv=b.work.levels[b.lvl];
  const s=b.locSel;
  return (s!=null&&s in (lv.locAll||{}))?s:bldLocCulture(lv,b.culture);
}
function bldLocRec(){
  const lv=state.bld.work.levels[state.bld.lvl];
  const c=bldLocSel();
  return (lv.locAll||{})[c]||(lv.locAll[c]={key:c?lv.name+'_'+c:lv.name,present:false,
                                            name:'',descr:'',descr_short:''});
}
function bldLocPick(c){ state.bld.locSel=c; bldTouched(); }
function bldLocSection(lv,orig){
  const b=state.bld,cur=bldLocSel(),rec=bldLocRec();
  const all=lv.locAll||{};
  const named=c=>{
    const r=all[c]||{};
    const tag=c===''?tt('buildings.shared_every_culture'):c;
    return `${tag}${bldLocPlaceholder(r)?tt('buildings.no_text'):''}`;
  };
  const owner=bldLocCulture(lv,b.culture);
  return `<div class="bsec"><h4>${tt('buildings.name_description_text_export_buildings_txt',{qm:qm(tt('buildings.which_key_in_export_buildings_txt'),tt('common.culture'))})}
      <select class="mini" style="flex:0 0 auto;max-width:250px"
        onchange="bldLocPick(this.value)">
        ${Object.keys(all).map(c=>`<option value="${esc(c)}" ${c===cur?'selected':''}
          >${esc(named(c))}</option>`).join('')}
      </select></span></h4>
      <div class="brow"><span class="k">${tt('buildings.name',{x:qm(tt('buildings.name_help',{key:rec.key}),tt('common.name'))})}</span>
        <input data-loc="name" value="${esc(rec.name)}" placeholder="${esc(orig.name)}"></div>
      <div class="brow"><span class="k">${tt('buildings.short_description',{x:qm(tt('buildings.short_description_help',{key:rec.key}),tt('buildings.short_description_2'))})}</span>
        <input data-loc="descr_short" value="${esc(rec.descr_short)}"></div>
      <div class="brow"><span class="k">${tt('buildings.description',{x:qm(tt('buildings.description_help',{key:rec.key}),tt('common.description'))})}</span>
        <textarea data-loc="descr" style="flex:1;min-height:56px;padding:4px 7px;font-size:12.5px"
          >${esc(rec.descr)}</textarea></div>
      <div class="bnote">${tt('buildings.editing',{key:esc(rec.key),x:rec.present?''
        :tt('buildings.new_this_key_is_not_in'),x2:cur===b.culture?tt('buildings.this_is_the_culture_the_browser')
        :cur===''?tt('buildings.shown_to_any_culture_that_has')
        :tt('buildings.the_browser_is_showing_which_reads',{culture:esc(b.culture||tt('buildings.the_shared_key')),x:esc((all[owner]||{}).key||lv.name)})})}</div></div>
`;
}
/* ---- can this building offer one faction too many units? ----
   M2TW's recruitment panel holds a limited number of units per building; past it
   the panel overflows and the game can crash on opening the settlement. That is
   a failure you only meet on the one save where enough conditions have lined up
   at once, so it is worth being told about while editing.

   The JS twin of buildings.recruitment_pressure, recomputed from the working
   copy so the count tracks pools as they are added, removed and re-gated.

   Two numbers, because they answer different questions. `always` is pools the
   faction gets with NO further condition - if that is over the limit the
   building is already broken. `most` assumes every event counter, hidden
   resource and settlement size holds at the same time; it is an upper bound on
   purpose, since which of a mod's conditions can truly coincide is not
   answerable from the EDB alone. */
function bldRecruitPressure(lv){
  const ov=state.bld.ov,fc=ov.faction_cultures||{},limit=ov.recruit_limit||32;
  const every=Object.keys(fc);
  const cultures=new Set(Object.values(fc));
  const ALL=(bldVocab().all_keyword||'all').toLowerCase();
  const most={},always={};
  [...lv.caps,...lv.fcaps].forEach(c=>{
    if(c.del||!c.pool)return;
    const conds=c.conds||[];
    const facs=conds.filter(x=>x.kind==='factions'&&!x.negate).flatMap(x=>x.values||[]);
    const gated=conds.some(x=>x.kind!=='factions');
    let who;
    if(!facs.length||facs.some(f=>(f||'').toLowerCase()===ALL))who=every;
    else{
      const s=new Set();
      facs.forEach(f=>{
        if(cultures.has(f))every.forEach(k=>{if(fc[k]===f)s.add(k);});
        else s.add(f);
      });
      who=[...s];
    }
    who.forEach(f=>{most[f]=(most[f]||0)+1; if(!gated)always[f]=(always[f]||0)+1;});
  });
  const rows=Object.keys(most)
    .filter(f=>most[f]>limit||(always[f]||0)>limit)
    .map(f=>({faction:f,most:most[f],always:always[f]||0}));
  rows.sort((a,b)=>b.always-a.always||b.most-a.most||a.faction.localeCompare(b.faction));
  return {limit,rows};
}
function bldPressureHtml(lv){
  const p=bldRecruitPressure(lv);
  if(!p.rows.length)return '';
  const hard=p.rows.filter(r=>r.always>p.limit);
  const rows=p.rows.slice(0,10).map(r=>`<div class="prow2 ${r.always>p.limit?'bad':''}">
      <span class="pf">${esc(bldFacLabel(r.faction))}</span>
      <span class="pn">${r.most}</span>
      <span class="pd">${r.always>p.limit
        ? `<b>${r.always}</b> ${tt('buildings.of_them_with_no_condition_at')}`
        : tt('buildings.unconditional_the_rest_need_every_gate',{always:r.always})}</span>
    </div>`).join('');
  return `<div class="ownwarn ${hard.length?'bad':''}" style="margin:0 0 8px">
    <b>${hard.length?tt('buildings.over_the_recruitment_limit'):tt('buildings.could_go_over_the_recruitment_limit')}</b>
    ${tt('buildings.m2tw_shows_at_most_units_per',{limit:p.limit,x:hard.length?'':tt('buildings.these_counts_assume_every_event_counter')})}
    <div class="plist">${rows}</div>
    ${p.rows.length>10?`<div class="count">${tt('buildings.and_more_faction_s',{rows:p.rows.length-10})}</div>`:''}
  </div>`;
}
function bldRequiresHelp(){
  const lv=state.bld.work.levels[state.bld.lvl];
  const txt=bldClauseText(lv.conds);
  return `<div class="bnote">${txt
    ? tt('buildings.written_into_the_edb_as_requires',{txt:esc(txt)})
    : tt('buildings.no_conditions_anyone_can_build_this')}</div>`;
}
/* Picking a faction brings its culture with it. Names and art are per culture,
   so filtering to Gondor while the grid still showed another culture's art read
   as Gondor owning that culture's buildings. Only a culture with a folder here is
   picked (the culture list is the folders, and anything else would show nothing),
   and only when it is not already the one on show. Returns whether it switched;
   bldSetCulture redraws, so the caller need not. */
function bldFollowCulture(faction){
  const b=state.bld; if(!b||!b.ov)return false;
  const f=(bldVocab().factions||[]).find(x=>x.code===faction);
  const c=f&&f.culture;
  if(!c||c===b.culture||!(b.ov.cultures||[]).includes(c))return false;
  bldSetCulture(c);
  return true;
}
// Switching culture changes both the art and the NAMES, and the names come from
// the server - so the grid is re-fetched. The open editor is not: it already
// holds every culture's text (`loc_all`), and re-fetching would throw away
// whatever has been typed into it.
async function bldSetCulture(c){
  const b=state.bld;
  b.culture=c; state.settings.bld_culture=c;
  api.post('/api/settings',{bld_culture:c});
  bldCulture.value=c; _bldFiltersFor='';
  if(b.d){ b.locSel=null; renderBuildingEditor(); }
  try{
    const ov=await api.get('/api/buildings?mod='+enc(b.mod)+'&culture='+enc(c));
    if(state.bld===b&&b.culture===c)b.ov=ov;    // keep any open editor's working copy
  }catch(e){}
  render();
}
// index into the level's combined cap list, so one data attribute addresses both
// the capability and the faction_capability arrays
function bldCapList(){
  const b=state.bld;
  const lv=b&&b.work&&b.work.levels[b.lvl];
  return lv?[...lv.caps,...lv.fcaps]:[];
}
/* ---- which recruit pools are shown ----
   A big level trains hundreds of units, almost all of them gated to one faction,
   so "who can train what here" is the question you actually arrive with. */
function bldPoolMatches(c){
  const sel=state.bld.poolFac;
  if(!sel||!sel.size)return true;
  const facs=(c.conds||[]).filter(x=>x.kind==='factions'&&!x.negate)
    .flatMap(x=>x.values||[]);
  if(!facs.length)return sel.has('(any)');      // no clause = anyone can train it
  const all=(bldVocab().all_keyword)||'all';
  if(facs.includes(all))return true;
  return facs.some(f=>sel.has(f));
}
function bldPoolFilterHtml(pools){
  const sel=state.bld.poolFac||new Set();
  const counts=new Map();
  let open=0;
  const all=(bldVocab().all_keyword)||'all';
  pools.forEach(c=>{
    const facs=(c.conds||[]).filter(x=>x.kind==='factions'&&!x.negate)
      .flatMap(x=>x.values||[]);
    if(!facs.length){open++;return;}
    new Set(facs).forEach(f=>counts.set(f,(counts.get(f)||0)+1));
  });
  // By unit count first, because "who trains the most here" is the question the
  // list is usually scanned for. A long roster is easier to FIND a name in
  // alphabetically, so the order is a remembered choice rather than a ruling.
  //
  // That choice used to be an entry in this very drop-down, which made it a
  // filter you had to pick to un-pick: choosing it closed the list, and the
  // sorted list only appeared when you opened it again. It is a button beside
  // the list now, so the order changes with the list still in front of you.
  const az=bldFacSort()==='az';
  const rows=[...counts.entries()].sort(az
    ? (a,b)=>bldFacName(a[0]).localeCompare(bldFacName(b[0]))
    : (a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  if(!rows.length&&!open)return '';
  const picked=sel.size
    ? [...sel].map(f=>f==='(any)'?'anyone':bldFacName(f)).join(', ').slice(0,40)
    : 'any';
  return qm(tt('buildings.faction_filter_help'),tt('buildings.faction_filter'))
    // A checklist, not a drop-down: a drop-down closes on every pick, so ticking
    // three factions was three trips. It stays open until a click lands outside.
    +`<details class="facpick" ${state.bld.poolFacOpen?'open':''}
      ontoggle="state.bld.poolFacOpen=this.open">
      <summary title="${esc(picked)}">${tt('buildings.faction',{picked:esc(picked)})}</summary>
      <div class="facpickpop">
        <div class="fphead"><span class="count">${sel.size?ttN('buildings.count_ticked',sel.size):tt('buildings.showing_every_unit')}</span>
          ${sel.size?`<button class="mini" style="margin-left:auto"
            onclick="bldPoolFacPick('(clear)')">${tt('buildings.show_everything')}</button>`:''}</div>
        ${open?bldPoolFacRow('(any)',tt('buildings.no_faction_clause'),open,sel):''}
        ${rows.map(([f,n])=>bldPoolFacRow(f,bldFacName(f),n,sel)).join('')}
      </div></details>
    <span class="viewtoggle" title="${ttA('buildings.which_order_the_faction_list_above')}">
      <button class="${az?'on':''}" ${az?'disabled':''}
        onclick="bldFacSortToggle()">${tt('buildings.a_to_z')}</button>
      <button class="${az?'':'on'}" ${az?'':'disabled'}
        onclick="bldFacSortToggle()">${tt('buildings.unit_count')}</button>
    </span>`;
}
function bldPoolFacRow(code,label,n,sel){
  return `<label><input type="checkbox" ${sel.has(code)?'checked':''}
      onchange="bldPoolFacPick('${q1(esc(code))}')">${esc(label)}<span class="count">${n}</span></label>`;
}
// A click outside the checklist closes it, the way a drop-down would. Guarded:
// test_buildings runs this file in node, where there is no document.
if(typeof document!=='undefined'&&document.addEventListener)document.addEventListener('mousedown',e=>{
  const open=document.querySelector('details.facpick[open]');
  if(!open||open.contains(e.target))return;
  open.open=false;
  if(state.bld)state.bld.poolFacOpen=false;
});
const bldFacSort=()=>((state.settings||{}).bld_facsort==='az'?'az':'count');
function bldFacSortToggle(){
  const v=bldFacSort()==='az'?'count':'az';
  state.settings.bld_facsort=v; api.post('/api/settings',{bld_facsort:v});
  bldRedrawLevel();
}
function bldPoolFacPick(v){
  const b=state.bld; if(!b)return;
  b.poolFac=b.poolFac||new Set();
  if(!v)return;
  if(v==='(clear)')b.poolFac.clear();
  else if(b.poolFac.has(v))b.poolFac.delete(v);
  else{ b.poolFac.add(v); bldFollowCulture(v); }
  bldRedrawLevel();
}
function bldSetView(v){
  const b=state.bld; if(!b)return;
  b.view=v;
  state.settings.bld_view=v; api.post('/api/settings',{bld_view:v});
  bldRedrawLevel();
}
/* Repaint the level the editor is on, or do nothing at all.
   Everything that changes how the recruitment list LOOKS lands here rather than
   reaching into `state.bld.work` itself: a mod switch nulls `state.bld` and a
   closed dialog leaves `work` null, and a control that survives either - the
   sidebar, a remembered setting, a keystroke - would otherwise throw on a stale
   object and take the whole page down with it. */
function bldRedrawLevel(){
  const b=state.bld;
  if(!b||!b.work||!b.d||!b.work.levels[b.lvl]||!b.d.levels[b.lvl])return;
  bldRenderBody(b.work.levels[b.lvl],b.d.levels[b.lvl]);
}
// The cached ownership answer for a pool, if one has been fetched - drawn as a
// small flag on the row rather than fetched eagerly for hundreds of units.
function bldPoolOwnFlag(c){
  const b=state.bld;
  const facs=(c.conds||[]).filter(x=>x.kind==='factions'&&!x.negate).flatMap(x=>x.values||[]);
  if(!facs.length)return '';
  const row=b.own[c.pool.unit+'|'+[...facs].sort().join(',')];
  if(!row||(!row.missing_ownership.length&&!row.missing_textures.length))return '';
  const bits=[];
  if(row.missing_ownership.length)bits.push(tt('buildings.not_owned_by_list',{list:row.missing_ownership.join(', ')}));
  if(row.missing_textures.length)bits.push(tt('buildings.no_texture_for_list',{list:row.missing_textures.join(', ')}));
  return `<span class="ownflag" title="${ttA('buildings.saving_fixes_this',{bits:esc(bits.join('; '))})}">⚠</span>`;
}
function bldPoolRow(c){
  const b=state.bld,i=bldCapList().indexOf(c);
  const info=b.d.units[(c.pool.unit||'').toLowerCase()];
  const missing=!info||info.missing;
  /* Two lines, not one. The row used to put the unit, four number boxes, the
     whole `requires` clause and five buttons side by side, and the clause is the
     only one of those with no natural width: a real one names half a dozen
     factions and a settlement level, so it was squeezed into whatever the fixed
     columns left over and read as an ellipsis. The numbers keep the top line,
     which is what the eye scans down; the clause gets a line to itself and the
     full width of the panel. */
  return `<div class="poolrow ${c.del?'gone':''} ${missing?'missing':''} ${
      bldBulkHas(c)?'picked':''}" data-cap="${i}">
    <div class="prtop">
      ${bldOrderHtml(i)}
      ${bldPickBox(c,i)}
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,c.pool.unit)}" alt="">
      <div class="who"><div class="un" title="${esc(c.pool.unit)}">${esc(info&&!missing?info.name:c.pool.unit)}</div>
        <div class="ut">${missing?`<span class="w-bad">${tt('buildings.not_in_this_mods_edu')}</span>`:esc(c.pool.unit)}</div></div>
      <div class="nums">
        <label>${qm(POOL_HELP.initial,POOL_LABEL.initial)}${POOL_LABEL.initial}${
          numBox('data-pool="initial"',c.pool.initial,'pool')}</label>
        <label>${qm(POOL_HELP.per_turn,POOL_LABEL.per_turn)}${POOL_LABEL.per_turn}${
          numBox('data-pool="per_turn"',c.pool.per_turn,'turns',
          `<span class="turns">= ${esc(poolTurns(c.pool.per_turn))}</span>`)}</label>
        <label>${qm(POOL_HELP.maximum,POOL_LABEL.maximum)}${POOL_LABEL.maximum}${
          numBox('data-pool="maximum"',c.pool.maximum,'pool')}</label>
        <label>${qm(POOL_HELP.experience,POOL_LABEL.experience)}${POOL_SHORT.experience}${
          numBox('data-pool="experience"',c.pool.experience,'1')}</label>
      </div>
      <div class="acts">
        <button title="${ttA('buildings.add_units_directly_under_this_one')}" onclick="bldInsertBelow(${i})">＋</button>
        ${bldPoolActs(c,i)}
        ${missing?'':`<button title="${ttA('buildings.open_this_unit_in_the_unit')}"
          onclick="openUnitFromBuilding('${q1(esc(c.pool.unit))}')">${tt('buildings.edit')}</button>`}
        <button class="${c.del?'':'danger'}" onclick="bldToggleDel(${i})"
          title="${c.del?tt('buildings.keep_this_recruit_pool'):tt('buildings.remove_this_recruit_pool')}">${c.del?'↺':'🗑'}</button>
      </div>
      ${c.faction?`<span class="badge">${tt('common.faction_2')}</span>`:''}
    </div>
    <div class="prbot">
      <span class="prk">${tt('buildings.requires_2')}</span>
      <div class="clausebar">
        <div class="sum">${bldClauseSummary(c.conds)}</div>
        ${bldPoolOwnFlag(c)}
        ${bldGateChip(c.conds)}
        <button class="reqbtn" onclick="bldEditClause('cap',${i})">✎</button>
        ${bldCopyBtn(i)}
      </div>
    </div></div>`;
}
function bldPoolCard(c){
  const b=state.bld,i=bldCapList().indexOf(c);
  const info=b.d.units[(c.pool.unit||'').toLowerCase()];
  const missing=!info||info.missing;
  return `<div class="ucard ${c.del?'gone':''} ${bldBulkHas(c)?'picked':''}" data-cap="${i}">
    <div class="top">
      ${bldPickBox(c,i)}
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,c.pool.unit)}" alt="">
      <div style="min-width:0">
        <div class="nm">${esc(info&&!missing?info.name:c.pool.unit)}</div>
        <div class="ty">${missing?`<span class="w-bad">${tt('buildings.not_in_this_mods_edu_2')}</span>`
          :esc([info.kind,info.class].filter(Boolean).join(' · ')||c.pool.unit)}</div>
      </div>
      ${bldPoolOwnFlag(c)}
    </div>
    <div class="stats">
      <label>${qm(POOL_HELP.initial,POOL_LABEL.initial)}${POOL_LABEL.initial}${
        numBox('data-pool="initial"',c.pool.initial,'pool')}</label>
      <label>${qm(POOL_HELP.per_turn,POOL_LABEL.per_turn)}${POOL_LABEL.per_turn}${
        numBox('data-pool="per_turn"',c.pool.per_turn,'turns')}</label>
      <label>${qm(POOL_HELP.maximum,POOL_LABEL.maximum)}${POOL_LABEL.maximum}${
        numBox('data-pool="maximum"',c.pool.maximum,'pool')}</label>
      <label>${qm(POOL_HELP.experience,POOL_LABEL.experience)}${POOL_SHORT.experience}${
        numBox('data-pool="experience"',c.pool.experience,'1')}</label>
    </div>
    <div class="turns" data-turns style="text-align:center">${tt('buildings.a_unit',{x:esc(poolTurns(c.pool.per_turn))})}</div>
    <div class="clausebar"><div class="sum">${bldClauseSummary(c.conds)}</div>${bldCopyBtn(i)}</div>
    <div class="acts">
      <button onclick="bldEditClause('cap',${i})">${tt('buildings.requires_3')}</button>
      ${bldPoolActs(c,i)}
      ${missing?'':`<button onclick="openUnitFromBuilding('${q1(esc(c.pool.unit))}')">${tt('buildings.unit_2')}</button>`}
      <button class="${c.del?'':'danger'}" onclick="bldToggleDel(${i})">${c.del?'↺':'🗑'}</button>
    </div></div>`;
}
/* The three things you reach for while looking at one recruit pool: put it in
   the settlement type's other half, push it up the rest of the chain, and see
   what every OTHER building gives the same unit. */
function bldPoolActs(c,i){
  const b=state.bld,twin=bldTwin(),above=b.work.levels.length-1-b.lvl;
  const unit=q1(esc(c.pool.unit));
  return `${twin&&bldTwinLevel()?`<button title="${ttA('buildings.copy_this_pool_into_the_half',{twin:esc(twin),settlement:esc(b.d.settlement==='city'?'castle':'city')})}"
    onclick="bldMirrorRowNow(${i})">⇄</button>`:''}
    ${above>0?`<button title="${ttA('buildings.add_this_unit_to_the_tier',{above})}"
      onclick="bldTiersRowNow(${i})">⇅</button>`:''}
    <button title="${ttA('buildings.compare_this_units_pool_replenishment_and')}"
      onclick="bldShowUnit('${unit}')">≡</button>`;
}

/* =========================================================================
   Bulk edit over recruit pools

   Nothing here is a new kind of edit - every one of these actions is something
   the single-row buttons already do. What it changes is the arithmetic: giving
   twenty freshly added units the same `requires factions { … }` was twenty trips
   through the clause dialog, and the twentieth was where the typo went in.

   The selection holds the capability OBJECTS, not their indices. Indices into
   bldCapList() shift the moment a row is added or a new row is dropped, and a
   selection that silently slides onto its neighbours is worse than none.
   ========================================================================= */
const bldBulk=()=>(state.bld.bulk||(state.bld.bulk={on:false,sel:new Set()}));
const bldBulkOn=()=>!!(state.bld&&state.bld.bulk&&state.bld.bulk.on);
const bldBulkHas=c=>bldBulkOn()&&bldBulk().sel.has(c);
// Only rows still in the level count - a new row that was dropped again is gone
// from lv.caps but may still be sitting in the Set.
function bldBulkSel(){
  const sel=bldBulk().sel;
  return bldCapList().filter(c=>c.pool&&sel.has(c));
}
function bldBulkToggle(){
  const bu=bldBulk(); bu.on=!bu.on;
  if(!bu.on)bu.sel.clear();
  bldRenderBodyNow();
}
function bldPickBox(c,i){
  if(!bldBulkOn())return '';
  return `<label class="pick" title="${ttA('buildings.tick_this_pool_for_the_bulk')}"><input type="checkbox"
    ${bldBulkHas(c)?'checked':''} onchange="bldBulkPick(${i},this.checked)"></label>`;
}
function bldBulkPick(i,on){
  const c=bldCapList()[i]; if(!c)return;
  on?bldBulk().sel.add(c):bldBulk().sel.delete(c);
  bldRenderBodyNow();
}
function bldBulkAll(on){
  const bu=bldBulk(),lv=state.bld.work.levels[state.bld.lvl];
  // "all" means all the filter is showing, not all three hundred the level has
  const shown=[...lv.caps,...lv.fcaps].filter(c=>c.pool&&bldPoolMatches(c));
  shown.forEach(c=>on?bu.sel.add(c):bu.sel.delete(c));
  if(!on)bu.sel.clear();
  bldRenderBodyNow();
}
const bldRenderBodyNow=()=>bldRenderBody(state.bld.work.levels[state.bld.lvl],
                                         state.bld.d.levels[state.bld.lvl]);
/* ---- carrying one row's clause to the others ----
   The clipboard lives on `state`, not on the building, so a clause copied out of
   the town watch can be pasted into the barracks - which is most of why anyone
   would copy one at all. It holds a deep copy: pasting must not hand every row a
   reference to the same terms, or editing one afterwards edits all of them. */
function bldCopyBtn(i){
  return `<button class="reqbtn" onclick="bldCopyCond(${i})"
    title="${ttA('buildings.copy_these_requirements_tick_other_units')}">⧉</button>`;
}
function bldCopyCond(i){
  const c=bldCapList()[+i]; if(!c)return;
  const name=(c.pool&&c.pool.unit)||c.keyword||tt('buildings.that_row');
  state.condClip={unit:name,conds:JSON.parse(JSON.stringify(c.conds||[])),
                  text:bldClauseText(c.conds)};
  // so the bar's "copy from" box keeps showing whoever it was last taken from,
  // whether that was picked in the box or by ⧉ on a row
  state.bld.copyFrom=(c.pool&&c.pool.unit)||'';
  const bu=bldBulk();
  if(!bu.on){bu.on=true;}                     // there is nowhere to paste it otherwise
  bldRenderBodyNow();
  toast(tt('buildings.copied_s_requirements_tick_the_units',{name,x:state.condClip.text?': '+state.condClip.text:tt('buildings.none_so_always')}),4200);
}
/* Put a clause onto one row. `replace` swaps it outright; `add` joins the new
   terms onto what is already there. M2TW evaluates a clause left to right with
   no brackets, so "add" really is a concatenation - the incoming terms are
   ANDed onto the end, and a term the row already carries is skipped rather than
   written twice. */
function bldCondsOnto(host,conds,mode){
  const incoming=JSON.parse(JSON.stringify(conds||[]));
  const base=mode==='add'?JSON.parse(JSON.stringify(host.conds||[])):[];
  const seen=new Set(base.map(c=>bldCondText(c)));
  const keep=incoming.filter(c=>{
    const t=bldCondText(c);
    if(mode==='add'&&seen.has(t))return false;
    seen.add(t); return true;
  });
  keep.forEach(c=>{ if(!c.join)c.join='and'; });
  const out=base.concat(keep);
  if(out.length)out[0].join='';
  host.conds=out; host.condEdited=true; host.requires=bldClauseText(out);
  return out;
}
function bldBulkPaste(){
  const sel=bldBulkSel(),clip=state.condClip;
  if(!clip||!sel.length)return;
  const mode=bldPasteMode();
  sel.forEach(h=>bldCondsOnto(h,clip.conds,mode));
  bldTouched();
  toast(ttN(mode==='add'?'buildings.requirements_added_to_units':'buildings.requirements_copied_onto_units',sel.length,{unit:clip.unit}));
}
const bldPasteMode=()=>(state.bld.pasteMode==='add'?'add':'replace');
function bldSetPasteMode(v){ state.bld.pasteMode=v; }
function bldBulkDelete(){
  const b=state.bld,sel=bldBulkSel(); if(!sel.length)return;
  const lv=b.work.levels[b.lvl];
  sel.forEach(c=>{
    c.del=true;
    // a row that was only ever added by this dialog just goes away
    if(c.line==null){ const from=c.faction?lv.fcaps:lv.caps;
      const i=from.indexOf(c); if(i>=0)from.splice(i,1); }
    bldBulk().sel.delete(c);
  });
  bldTouched();
  toast(ttN('buildings.recruit_pools_marked_for_removal',sel.length));
}
// Only the boxes you actually filled in are written - a blank one leaves that
// number alone, so "give these twelve units max 4" doesn't also zero their
// starting points.
function bldBulkNums(){
  const b=state.bld,sel=bldBulkSel(),n=b.bulkNums||{};
  const keys=['initial','per_turn','maximum','experience'].filter(k=>(n[k]||'').trim()!=='');
  if(!sel.length)return;
  if(!keys.length){toast(tt('buildings.fill_in_at_least_one_of'));return;}
  sel.forEach(c=>keys.forEach(k=>{c.pool[k]=n[k].trim();}));
  bldTouched();
  toast(ttN('buildings.pool_numbers_set_on_pools',sel.length,{labels:keys.map(k=>POOL_LABEL[k]||k).join(', ')}));
}
/* What the three recruitment numbers are CALLED, in one place.

   They used to be labelled by shape rather than by job: "start / per turn / max"
   describes the arithmetic and says nothing about what the number does to the
   game, and each screen had spelt it differently anyway. These are the names
   every screen in the toolkit now uses, so the number you set on a row is the
   number you recognise in the comparison panel and in the bulk editor. */
const POOL_LABEL={initial:tt('buildings.initial_pool'),per_turn:tt('buildings.replenish_rate'),
                  maximum:tt('buildings.max_pool'),experience:tt('common.experience')};
//: The same names where a row has no width to spare for the long one.
const POOL_SHORT={initial:tt('buildings.initial_pool'),per_turn:tt('buildings.replenish_rate'),
                  maximum:tt('buildings.max_pool'),experience:'XP'};
/* Which unit a clause is taken FROM is its own choice, not "whichever you ticked
   first": the unit you want to copy is usually one you have NOT ticked, because
   the ticks are the units you are about to paste onto. So it is a box over every
   pool on the level - ticked ones marked - rather than a button. */
function bldCopySelect(sel){
  const b=state.bld,list=bldCapList();
  const pools=list.map((c,i)=>({c,i})).filter(x=>x.c.pool&&!x.c.del);
  if(!pools.length)return '';
  const name=c=>{
    const info=b.d.units[(c.pool.unit||'').toLowerCase()];
    return (info&&!info.missing?info.name:c.pool.unit)||c.pool.unit;
  };
  const byUnit=pools.find(x=>x.c.pool.unit===b.copyFrom);
  const cur=byUnit?byUnit.i:(sel.length?list.indexOf(sel[0]):-1);
  return `<span class="lbl2">${tt('buildings.copy_from')}</span>
    <select onchange="bldCopyCond(this.value)" style="max-width:220px"
      title="${ttA('buildings.take_this_units_requirements_onto_the')}">
      ${pools.map(x=>`<option value="${x.i}" ${x.i===cur?'selected':''}
        >${bldBulkHas(x.c)?'✓ ':''}${esc(name(x.c))}</option>`).join('')}
    </select>`;
}
function bldBulkBar(shown){
  if(!bldBulkOn())return '';
  const b=state.bld,sel=bldBulkSel(),n=sel.length,clip=state.condClip;
  const bn=b.bulkNums||(b.bulkNums={initial:'',per_turn:'',maximum:'',experience:''});
  const num=k=>`<label>${POOL_LABEL[k]}<input data-bulknum="${k}" value="${esc(bn[k])}"
    placeholder="0" inputmode="decimal"></label>`;
  return `<div class="bulkbar">
    <span class="n">${tt('buildings.selected',{x:n})}</span>
    <button onclick="bldBulkAll(true)">${tt('buildings.tick_all_shown',{shown_n:shown.length})}</button>
    <button onclick="bldBulkAll(false)" ${n?'':'disabled'}>${tt('common.clear')}</button>
    <button class="primary" ${n?'':'disabled'} onclick="bldBulkClause()"
      title="${ttA('buildings.edit_one_requires_clause_and_put')}">${tt('buildings.requirements_for',{x:n})}</button>
    ${bldCopySelect(sel)}
    <button ${clip&&n?'':'disabled'} onclick="bldBulkPaste()"
      title="${clip?esc(tt('buildings.paste_unit_requirements',{unit:clip.unit,text:clip.text||tt('buildings.none_so_always_2')}))
                  :tt('buildings.copy_a_units_requirements_first')}">${tt('buildings.paste',{clip:clip?` ${esc(clip.unit)}’s`:''})}</button>
    <select onchange="bldSetPasteMode(this.value)" title="${ttA('buildings.what_pasting_does_to_what_the')}">
      <option value="replace" ${bldPasteMode()==='replace'?'selected':''}>${tt('buildings.replace_theirs')}</option>
      <option value="add" ${bldPasteMode()==='add'?'selected':''}>${tt('buildings.add_to_theirs')}</option>
    </select>
    <button class="danger" ${n?'':'disabled'} onclick="bldBulkDelete()">${tt('buildings.remove',{x:n})}</button>
    <div class="bnote" style="flex:1 1 100%;margin:0">${clip
      ? `${tt('buildings.clipboard',{unit:esc(clip.unit)})} <code>${esc(clip.text||'always')}</code>`
      : tt('buildings.copy_a_clause_off_one_unit')}</div>
    <div class="bnums">${['initial','per_turn','maximum','experience'].map(num).join('')}
      <button ${n?'':'disabled'} onclick="bldBulkNums()">${tt('buildings.apply_numbers_to',{x:n})}</button>
      <span class="hint">${tt('buildings.blank_boxes_are_left_alone')}</span></div>
  </div>`;
}
/* One clause dialog over many rows. It opens on what they already say when they
   all say the same thing - the common case straight after adding a batch, where
   every one of them carries its own ownership and you are about to narrow that
   to one faction. When they disagree it opens empty rather than picking a winner
   arbitrarily. */
function bldBulkClause(){
  const b=state.bld,hosts=bldBulkSel();
  if(!hosts.length)return;
  const first=bldClauseText(hosts[0].conds);
  const same=hosts.every(h=>bldClauseText(h.conds)===first);
  const seed=same?JSON.parse(JSON.stringify(hosts[0].conds||[])):[];
  b.clause={hosts,kind:'bulk',index:-1,
            conds:seed,was:JSON.parse(JSON.stringify(seed)),
            units:hosts.map(h=>h.pool&&h.pool.unit).filter(Boolean),
            unit:'',mode:same?'replace':'add',same,pick:null};
  // The clause dialog's own slot: Cancel and Use read `cstash`, so parking the
  // screen in `stash` left them nothing to put back but "undefined".
  bldClauseStash();
  renderClauseDialog();
  bldClauseOwnership();
}
function bldClauseMode(v){ state.bld.clause.mode=v; renderClauseDialog(); }

/* ---- the upgrade graph ----
   A line is not always a straight chain. Some branch (A -> B -> D and A -> C -> E),
   and at least one in DaC is a single root with every other level hanging off it
   (A -> B, C, D, E). So rather than assume a ladder, the levels are laid out by
   depth from whichever ones nothing upgrades into. */
function bldUpgradeGraph(){
  const b=state.bld,levels=b.work.levels;
  const idx=new Map(levels.map((lv,i)=>[lv.name,i]));
  const into=new Map(levels.map(lv=>[lv.name,[]]));
  levels.forEach(lv=>lv.upgrades.forEach(u=>{
    const name=u.split(/\s+/)[0];
    if(into.has(name))into.get(name).push(lv.name);
  }));
  const roots=levels.filter(lv=>!into.get(lv.name).length).map(lv=>lv.name);
  const depth=new Map();
  const walk=(name,d,seen)=>{
    if(seen.has(name))return;                 // a cycle in a hand-edited EDB
    seen.add(name);
    depth.set(name,Math.max(depth.get(name)||0,d));
    const lv=levels[idx.get(name)];
    (lv?lv.upgrades:[]).forEach(u=>{
      const n=u.split(/\s+/)[0];
      if(idx.has(n))walk(n,d+1,seen);
    });
    seen.delete(name);
  };
  (roots.length?roots:[levels[0]&&levels[0].name]).forEach(r=>r&&walk(r,0,new Set()));
  levels.forEach(lv=>{if(!depth.has(lv.name))depth.set(lv.name,0);});
  const tiers=[];
  depth.forEach((d,name)=>{(tiers[d]=tiers[d]||[]).push(name);});
  return {tiers,idx,into,depth};
}
function bldUpgradesSection(lv,orig){
  const b=state.bld,g=bldUpgradeGraph();
  const idx=g.idx;
  const node=name=>{
    const i=idx.get(name);
    const t=i==null?name:bldLevelLabel(i);
    return `<div class="pnode ${i===b.lvl?'on':''}" onclick="bldPickLevel(${i})"
      title="${ttA('buildings.open_2',{x:esc(t)})}">
      <img loading="lazy" onerror="iconRetry(this)" src="${bldIcon(name,'small')}" alt="">
      <div><div class="t">${esc(t)}</div><div class="n">${esc(name)}</div></div></div>`;
  };
  // what THIS level upgrades into, editable; only ever levels further along the
  // line's own `levels` order, because M2TW upgrades never go backwards
  const here=lv.upgrades.map(bldUpgName);
  const forward=b.d.levels.map((l,i)=>l.name)
    .filter((n,i)=>i>b.lvl&&!here.includes(n));
  return `<div class="bsec"><h4>${tt('buildings.upgrade_path')}
      <span class="count">${g.tiers.length>1?g.tiers.length+' tiers':tt('buildings.one_tier')}</span></h4>
    <div class="pathwrap">${g.tiers.map((names,d)=>`
      <div class="prow">${d?'<span class="parrow">↳</span>':''}
        ${names.map(node).join(d?`<span class="pbranch">${tt('buildings.or')}</span>`:'<span class="parrow">·</span>')}
      </div>`).join('')}</div>
    <div class="bnote">${tt('buildings.click_any_building_to_open_it')}</div>
    <h4 style="margin-top:12px">${tt('buildings.upgrades_into',{x:esc(bldLevelLabel(b.lvl))})}
      <span class="n">${here.length}</span></h4>
    <div class="upglist" id="bldUpg">${here.length?lv.upgrades.map((u,i)=>{
        const name=bldUpgName(u);
        const j=idx.get(name);
        const conds=(lv.upgConds&&lv.upgConds[i])||[];
        return `<div class="upgrow">
          <span class="un">${j!=null?`<a class="ulink" onclick="bldPickLevel(${j})">${esc(name)}</a>`
            :`<span class="w-bad" title="${ttA('buildings.no_level_of_this_line_is')}">${esc(name)}</span>`}</span>
          <div class="clausebar" style="flex:1;min-width:110px">
            <div class="sum">${bldClauseSummary(conds)}</div>
            <button class="reqbtn" onclick="bldEditClause('upgrade',${i})"
              title="${ttA('buildings.who_takes_this_branch_an_upgrade')}">✎</button>
          </div>
          <button class="x danger" onclick="bldUpgRemove(${i})"
            title="${ttA('buildings.stop_upgrading_into_this')}">🗑</button></div>`;
      }).join(''):`<div class="upgrow"><span class="count">${tt('buildings.nothing_this_is_the_end_of')}</span></div>`}
    </div>
    ${forward.length?`<div class="brow" style="margin-top:6px">
      <select class="mini" id="upgAdd" style="flex:0 0 260px">
        <option value="">${tt('buildings.also_upgrade_into')}</option>
        ${forward.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join('')}
      </select><span class="count">${tt('buildings.only_levels_later_in_the_line')}</span></div>`
      :`<div class="bnote">${tt('buildings.this_is_the_last_level_in')}</div>`}
  </div>`;
}
/* An `upgrades` entry is a level name and, sometimes, a clause of its own:
   `ce_wooden_wall requires event_counter cex_avail_wooden_wall_erebor 1`. The
   level is the first word - the server's `buildings.upgrade_name` says the same
   thing, and both are wanted, because the page draws the row and the file
   writes it. */
const bldUpgName=u=>String(u||'').split(/\s+/)[0]||'';
function bldUpgRemove(i){
  const lv=state.bld.work.levels[state.bld.lvl];
  lv.upgrades.splice(i,1);
  if(lv.upgConds)lv.upgConds.splice(i,1);
  bldTouched();
}
function bldUpgAdd(name){
  if(!name)return;
  const lv=state.bld.work.levels[state.bld.lvl];
  lv.upgrades.push(name);
  (lv.upgConds=lv.upgConds||[]).push([]);
  bldTouched();
}
/* The keyword picker, in groups. There are 60 of them and they were one flat
   alphabetical list, which is a list you read rather than choose from -
   `construction_cost_bonus_stone` and `weapon_melee_blade` are not neighbours in
   anybody's head. The grouping is the one thing worth taking from the reference
   tool's EDB half; the hint carries the range the engine accepts beside it. */
function bldCapOptions(current){
  const b=state.bld,caps=b.ov.capabilities||[];
  const groups=b.ov.capability_groups||['Other'];
  const known=caps.map(x=>x.keyword);
  const out=groups.map(g=>{
    const rows=caps.filter(x=>(x.group||tt('buildings.other'))===g);
    if(!rows.length)return '';
    return `<optgroup label="${esc(g)}">${rows.map(x=>
      `<option value="${esc(x.keyword)}" ${x.keyword===current?'selected':''}
        title="${esc(x.help||'')}">${esc(x.keyword)}${
        x.range?` (${esc(x.range)})`:''}</option>`).join('')}</optgroup>`;
  }).join('');
  // a keyword this mod uses that our list has never heard of stays selectable
  return out+(known.includes(current)?''
    :`<optgroup label="In this file"><option value="${esc(current)}" selected
        >${esc(current)}</option></optgroup>`);
}
function bldCapRow(c){
  const b=state.bld,i=bldCapList().indexOf(c);
  const meta=b.ov.capabilities.find(x=>x.keyword===c.keyword)||{};
  const help=(meta.help||'')+(meta.range?`  (${meta.range})`:'');
  return `<div class="caprow ${c.del?'gone':''}" data-cap="${i}">
    ${bldOrderHtml(i)}
    ${qm(help.trim()||tt('buildings.a_capability_this_level_gives_the'),c.keyword)}
    <select class="kw" data-kw>${bldCapOptions(c.keyword)}</select>
    ${qm(tt('buildings.write_the_value_as_bonus_n'),'bonus')}
    <label class="chk"><input type="checkbox" data-bonus ${c.bonus?'checked':''}> ${tt('buildings.bonus')}</label>
    ${numBox(tt('buildings.class_val_data_val'),c.value,'1')}
    <div class="clausebar" style="flex:1;min-width:110px">
      <div class="sum">${bldClauseSummary(c.conds)}</div>
      ${bldGateChip(c.conds)}
      <button class="reqbtn" onclick="bldEditClause('cap',${i})">✎</button>
    </div>
    ${c.faction?`<span class="badge">${tt('common.faction_2')}</span>`:''}
    <button class="x" title="${ttA('buildings.add_a_capability_directly_under_this')}" onclick="bldInsertBelow(${i})">＋</button>
    <button class="x ${c.del?'':'danger'}" onclick="bldToggleDel(${i})">${c.del?'↺':'🗑'}</button>
    </div>`;
}

/* ---- order (Phase 51) ----
   The list's order is the file's order: `_plan_capabilities` writes the rows
   in the order they are sent, and the recruitment panel in game lists units in
   the order the EDB gives them. So a row moves two ways - drag by the grip, or
   one step with the arrows - and a new one can go straight under the row it
   belongs beside instead of at the bottom of a list of eighty.

   A row only moves inside its own block. `capability` and `faction_capability`
   are two blocks in the file, and the combined list here shows them end to
   end; dragging one into the other would be a different edit (a change of
   scope) dressed up as a move. */
function bldOrderHtml(i){
  return `<span class="ordgrip" draggable="true" data-grip="${i}"
      title="${ttA('buildings.drag_to_move_this_line_this')}">⠿</span>
    <span class="ordbtns"><button title="${ttA('buildings.move_up_one')}" onclick="bldMoveStep(${i},-1)">▲</button><button
      title="${ttA('buildings.move_down_one')}" onclick="bldMoveStep(${i},1)">▼</button></span>`;
}
function bldArrOf(c){
  const lv=state.bld.work.levels[state.bld.lvl];
  return c.faction?lv.fcaps:lv.caps;
}
function bldMoveCap(c,t,after){
  if(!c||!t||c===t)return false;
  const arr=bldArrOf(c);
  if(arr!==bldArrOf(t)){
    toast(tt('buildings.one_of_these_is_in_the'),4200);
    return false;
  }
  arr.splice(arr.indexOf(c),1);
  arr.splice(arr.indexOf(t)+(after?1:0),0,c);
  bldTouched();
  return true;
}
// One step, past the neighbour the user can SEE: the faction filter hides rows,
// and an arrow that swapped with an invisible one would look like it did nothing.
function bldMoveStep(i,dir){
  const list=bldCapList(),row=document.querySelector(`#bldBody [data-cap="${i}"]`);
  if(!row)return;
  const sib=dir<0?row.previousElementSibling:row.nextElementSibling;
  if(!sib||sib.dataset.cap==null)return;
  bldMoveCap(list[i],list[+sib.dataset.cap],dir>0);
}
function bldInsertBelow(i){
  const c=bldCapList()[i]; if(!c)return;
  if(c.pool){ state.bld.insertAfter=c; bldAddPoolDialog(); return; }
  const arr=bldArrOf(c);
  arr.splice(arr.indexOf(c)+1,0,{line:null,keyword:'law_bonus',args:'',requires:'',
    bonus:true,value:'1',pool:null,comment:'',faction:c.faction,del:false});
  bldTouched();
}
// Drag, bound by delegation on the two lists: they are rebuilt on every edit.
function bldWireOrder(){
  const b=state.bld;
  const clear=box=>box.querySelectorAll('.dragging,.dropb,.dropa')
    .forEach(x=>x.classList.remove('dragging','dropb','dropa'));
  ['bldPools','bldCaps'].forEach(id=>{
    const box=document.getElementById(id); if(!box)return;
    const target=ev=>{
      if(b.drag==null||b.drag.box!==id)return null;
      const row=ev.target.closest&&ev.target.closest('[data-cap]');
      if(!row||!box.contains(row))return null;
      const r=row.getBoundingClientRect();
      return {row,after:ev.clientY>r.top+r.height/2};
    };
    box.ondragstart=ev=>{
      const g=ev.target.closest&&ev.target.closest('[data-grip]');
      if(!g)return;
      b.drag={box:id,i:+g.dataset.grip};
      ev.dataTransfer.effectAllowed='move';
      ev.dataTransfer.setData('text/plain','');
      const row=g.closest('[data-cap]');
      if(row){ row.classList.add('dragging'); ev.dataTransfer.setDragImage(row,14,14); }
    };
    box.ondragover=ev=>{
      const t=target(ev); if(!t)return;
      ev.preventDefault();
      box.querySelectorAll('.dropb,.dropa').forEach(x=>x.classList.remove('dropb','dropa'));
      t.row.classList.add(t.after?'dropa':'dropb');
    };
    box.ondrop=ev=>{
      const t=target(ev),from=b.drag; b.drag=null; clear(box);
      if(!t)return;
      ev.preventDefault();
      const list=bldCapList();
      bldMoveCap(list[from.i],list[+t.row.dataset.cap],t.after);
    };
    box.ondragend=()=>{ b.drag=null; clear(box); };
  });
}
function bldToggleDel(i){
  const c=bldCapList()[i]; c.del=!c.del;
  // a row that was only ever added by this dialog just goes away
  if(c.del&&c.line==null){
    const lv=state.bld.work.levels[state.bld.lvl];
    const from=c.faction?lv.fcaps:lv.caps;
    from.splice(from.indexOf(c),1);
  }
  bldTouched();
}
function bldTouched(){
  state.bld.planStale=!!state.bld.plan;
  const b=state.bld;
  // The building form is not on screen while another panel has the modal, and
  // its body element does not exist. Staging from over there redraws its own
  // panel, and the form is rebuilt from the same working copy on the way back.
  // `stash` is what every such panel sets, so this covers the ones written after
  // it as well as the two that were named here.
  if(b.cmp||b.vc||b.stash)return;
  bldRenderBody(b.work.levels[b.lvl],b.d.levels[b.lvl]);
  bldCvFollow();
}
/* The working copy as it was when the building opened, so every widget can say
   which of its values is yours. b.orig is the JSON of that moment; it is parsed
   once and cached, not per keystroke. */
function bldBaseLevel(){
  const b=state.bld;
  if(b._baseFor!==b.orig){ b._base=JSON.parse(b.orig); b._baseFor=b.orig; }
  const lv=b._base.levels[b.lvl]||{caps:[],fcaps:[]};
  return [...lv.caps,...lv.fcaps];
}
function bldWire(){
  const b=state.bld,lv=b.work.levels[b.lvl],list=bldCapList();
  const body=document.getElementById('bldBody');
  const mark=(el,changed)=>el.classList.toggle('changed',!!changed);
  const orig=b.d.levels[b.lvl];
  body.querySelectorAll('[data-scalar]').forEach(el=>{
    const key=el.dataset.scalar;
    mark(el,(el.value||'')!==(orig.scalars[key]||''));
    el.oninput=el.onchange=()=>{
      const v=el.value.trim();
      if(v)lv.scalars[key]=v; else delete lv.scalars[key];
      mark(el,v!==(orig.scalars[key]||'')); bldDirtyNote();};
  });
  const st=body.querySelector('[data-settlement]');
  mark(st,st.value!==orig.settlement);
  st.onchange=()=>{lv.settlement=st.value;mark(st,st.value!==orig.settlement);bldDirtyNote();};
  const upAdd=document.getElementById('upgAdd');
  if(upAdd)upAdd.onchange=()=>{bldUpgAdd(upAdd.value);};
  // The bulk bar's four numbers are staged on the building, not on any row, so
  // ticking another unit (which redraws the bar) doesn't wipe what was typed.
  body.querySelectorAll('[data-bulknum]').forEach(el=>{
    el.oninput=()=>{(b.bulkNums||(b.bulkNums={}))[el.dataset.bulknum]=el.value;};
  });
  const locC=bldLocSel(),locWas=((orig.loc_all||{})[locC])||{};
  body.querySelectorAll('[data-loc]').forEach(el=>{
    const key=el.dataset.loc;
    mark(el,el.value!==(locWas[key]||''));
    el.oninput=()=>{bldLocRec()[key]=el.value;
      mark(el,el.value!==(locWas[key]||''));bldDirtyNote();};
  });
  // A capability is matched to its baseline by the EDB LINE it came from, not by
  // its position: adding a pool pushes onto lv.caps, which shifts every
  // faction_capability's index in the combined list and would mis-pair them.
  const baseCaps=new Map();
  bldBaseLevel().forEach(c=>{ if(c.line!=null)baseCaps.set(c.line,c); });
  body.querySelectorAll('[data-cap]').forEach(row=>{
    const c=list[+row.dataset.cap]; if(!c)return;
    const was=c.line==null?null:baseCaps.get(c.line);   // null = a row you added
    const rowMark=()=>row.classList.toggle('changed',
      !!row.querySelector('.changed')||c.line==null||c.del);
    row.querySelectorAll('[data-pool]').forEach(el=>{
      const k=el.dataset.pool;
      const orig=()=>String((was&&was.pool&&was.pool[k])!=null?was.pool[k]:'');
      const diff=()=>!was||el.value.trim()!==orig();
      mark(el,diff());
      el.oninput=()=>{c.pool[k]=el.value.trim();
        // the grid card keeps its "a unit every N turns" line under the boxes
        if(k==='per_turn')row.querySelectorAll('[data-turns]')
          .forEach(t=>{t.textContent=tt('buildings.a_unit',{x:poolTurns(el.value)});});
        mark(el,diff()); rowMark(); bldDirtyNote();};});
    const kw=row.querySelector('[data-kw]');
    if(kw){ mark(kw,!was||kw.value!==was.keyword);
      kw.onchange=()=>{c.keyword=kw.value;bldTouched();}; }
    const bo=row.querySelector('[data-bonus]');
    if(bo){ mark(bo,!was||bo.checked!==!!was.bonus);
      bo.onchange=()=>{c.bonus=bo.checked;mark(bo,!was||bo.checked!==!!was.bonus);
        rowMark();bldDirtyNote();}; }
    const val=row.querySelector('[data-val]');
    if(val){ const diff=()=>!was||val.value.trim()!==String(was.value==null?'':was.value);
      mark(val,diff());
      val.oninput=()=>{c.value=val.value.trim();mark(val,diff());rowMark();bldDirtyNote();}; }
    rowMark();
  });
  wireNumBoxes(body);
  bldWireOrder();
}
function bldDirtyNote(){
  paintDirty();
  const b=state.bld; if(!b)return;
  b.planStale=!!b.plan;
  // 94a: the level chip is a summary too, so it follows the burst, not each click
  clearTimeout(b._chipT);
  const lvl=b.lvl;
  b._chipT=setTimeout(()=>{
    if(state.bld!==b)return;
    const chip=document.querySelectorAll('.lvchip')[lvl];
    if(chip)chip.classList.toggle('dirty',bldLevelDirty(lvl));
  },120);
  bldCvFollow();
}
/* Keep the text pane in step with the boxes.

   Every other editor that adopted the pane calls `cvFromGui` the moment one of
   its boxes changes, which is what makes the pane a promise about the bytes a
   save would write rather than a picture of the record as it opened. This one
   never did: cost, culture, name, a `requires` term, a recruit pool's numbers -
   all of it changed the working copy, none of it reached the pane, and the text
   beside the form went on showing the file. It is called from the two places
   every change in this editor already goes through, so a new control gets it
   without knowing the pane exists.

   `cvFromGui` is itself debounced and does nothing while the caret is IN the
   pane, so this is safe to call on every keystroke. */
function bldCvFollow(){
  const b=state.bld;
  if(b&&b.cv&&!b.cmp)cvFromGui(b.cv);
}
function bldAddCap(){
  const lv=state.bld.work.levels[state.bld.lvl];
  lv.caps.push({line:null,keyword:'law_bonus',args:'',requires:'',bonus:true,value:'1',
                pool:null,comment:'',faction:false,del:false});
  if(!foldIsOpen('bld.caps'))foldSet('bld.caps',true);
  bldTouched();
}

/* =========================================================================
   `requires` clauses, as structure

   A clause is a flat list of terms joined left-to-right by and/or - M2TW has no
   precedence, so there is no tree to draw. Each term names something declared
   elsewhere in the mod (a faction, an event counter, a hidden resource) by its
   CODE name, and a typo there is invisible: the game doesn't complain, the
   building simply never becomes available. So every term is edited by picking
   from the mod's own lists, shown by real name with the code in brackets.

   Anything the parser didn't recognise stays as raw text rather than being
   dropped - a couple of real mods have malformed clauses and they must survive
   a round trip untouched.
   ========================================================================= */

const COND_LABEL={factions:tt('common.factions'),hidden_resource:tt('buildings.hidden_resource'),
  resource:tt('buildings.trade_resource'),event_counter:tt('buildings.event'),region_religion:tt('buildings.region_religion'),
  building_present_min_level:tt('buildings.building_present_min_level'),
  building_present:tt('buildings.building_present'),settlement_min:tt('buildings.settlement_size'),
  market_level:tt('buildings.market_level'),raw:tt('buildings.custom_text')};

const bldVocab=()=>((state.bld&&state.bld.ov&&state.bld.ov.vocab)||{});
// A `factions { }` entry may be a faction, a whole culture, or the keyword
// `all`; the label says which, since a culture quietly covers several factions.
function bldFacName(code){
  const v=bldVocab();
  if(code===(v.all_keyword||'all'))return tt('common.all_factions');
  const f=(v.factions||[]).find(x=>x.code===code);
  if(f)return facTwoNames(f.code,f.name);
  const c=(v.cultures||[]).find(x=>x.code===code);
  if(c)return tt('buildings.culture',{x:c.name?c.name+' ':'',code:c.code});
  return code;
}
function bldEventName(name){
  const e=(bldVocab().events||[]).find(x=>x.name===name);
  return e&&e.title?`${e.title} (${e.name})`:name;
}
// The JS side of Condition.text() in unittransfer/buildings.py. Kept in step
// with it because the page previews a clause before the server ever emits one;
// the server's version is what actually gets written.
function bldCondText(c){
  if(c.kind==='raw')return c.raw||'';
  const body=c.kind==='factions'
    ? 'factions {'+(c.values||[]).map(v=>' '+v+',').join('')+' }'
    : [c.kind].concat((c.values||[]).filter(v=>v!=='')).join(' ');
  return (c.negate?'not ':'')+body;
}
function bldClauseText(conds){
  return (conds||[]).map((c,i)=>(i?` ${c.join||'and'} `:'')+bldCondText(c)).join('').trim();
}
// One readable line for a row that has no room for the full editor.
function bldClauseSummary(conds){
  if(!conds||!conds.length)return `<span class="count">${tt('buildings.always')}</span>`;
  return conds.map((c,i)=>{
    const j=i?`<span class="cj">${esc(c.join||'and')}</span> `:'';
    return j+`<span class="cterm${c.negate?' neg':''}">${esc(bldCondSummary(c))}</span>`;
  }).join(' ');
}
function bldCondSummary(c){
  const v=c.values||[],n=c.negate?'not ':'';
  switch(c.kind){
    case 'factions':{
      const names=v.map(x=>{const f=(bldVocab().factions||[]).find(y=>y.code===x);
        return f&&f.name?f.name:x;});
      return n+(names.length>3?`${names.slice(0,3).join(', ')} +${names.length-3}`
                              :names.join(', ')||'nobody');}
    case 'event_counter':{
      const e=(bldVocab().events||[]).find(x=>x.name===v[0]);
      const nm=e&&e.title?e.title:v[0];
      return (v[1]==='0'?'before ':'after ')+(c.negate?'NOT ':'')+nm;}
    case 'region_religion': return tt('buildings.region',{x:n,x2:v[1],x3:v[0]});
    case 'hidden_resource': return tt('buildings.hidden',{x:n,x2:v[0]});
    case 'resource': return tt('buildings.resource',{x:n,x2:v[0]});
    case 'building_present_min_level': return tt('buildings.has',{x:n,x2:v[0],x3:v[1]});
    case 'building_present': return `${n}has ${v[0]}`;
    default: return n+bldCondText(Object.assign({},c,{negate:false}));
  }
}
/* ---- the clause dialog ----
   Opened from a level or from one recruit pool. `ctx.conds` is edited in place
   and `ctx.done()` is called on close, so the caller doesn't have to thread the
   value back. The building editor's markup is stashed and restored, the same
   trick the unit picker uses. */
function bldEditClause(kind,index){
  const b=state.bld,lv=b.work.levels[b.lvl];
  // An upgrade row has no host object of its own - the entry is a string in
  // `lv.upgrades`. So it gets a stand-in whose conds the dialog edits, and
  // bldClauseApply writes the two back into the string as one.
  const host=kind==='level'?lv
    :kind==='upgrade'?{conds:(lv.upgConds&&lv.upgConds[index])||[],requires:'',
                       upgIndex:index}
    :bldCapList()[index];
  if(!host)return;
  const unit=(host.pool&&host.pool.unit)||'';
  b.clause={host,kind,index,conds:JSON.parse(JSON.stringify(host.conds||[])),
            // what the clause said on the way in, so every widget in here can
            // show which of its values YOU changed
            was:JSON.parse(JSON.stringify(host.conds||[])),
            unit,units:unit?[unit]:[],pick:null};
  bldClauseStash();
  renderClauseDialog();
  bldClauseOwnership();
}
/* The clause dialog keeps its OWN snapshot of what it covered up.
   It used to borrow `b.stash`, which the add-unit picker and the unit view also
   use - and the unit view can open this dialog on top of itself, so the two
   took turns clearing one slot and the building form underneath was lost. One
   slot per layer, and the nesting stops mattering. */
function bldClauseStash(){
  const b=state.bld;
  b.cstashScroll=stashPlace();   // come back to the row you opened, not the top
  b.cstash=document.getElementById('modal').innerHTML;
}
function bldClauseUnstash(){
  const b=state.bld;
  document.getElementById('modal').innerHTML=b.cstash; b.cstash=null;
  usePlace(b.cstashScroll); b.cstashScroll=null;
}
function bldClauseCancel(){
  const b=state.bld,unit=b.clause&&b.clause.kind==='unit';
  // The unit editor's Recruitment tab has no stash: its modal holds a live
  // WebGL column that a markup snapshot would replace with a dead copy, so it
  // is rebuilt from state instead. See edRecEditReq.
  if(b.clause&&b.clause.kind==='edrec'){ b.clause=null; renderEditor(); return; }
  bldClauseUnstash(); b.clause=null;
  // The stash is markup, not a live panel: whichever screen we came from has to
  // be drawn again or its inputs come back unwired.
  if(unit)bldUnitRender(); else bldRenderBody(b.work.levels[b.lvl],b.d.levels[b.lvl]);
}
function bldClauseApply(){
  const b=state.bld,c=b.clause;
  if(c.kind==='bulk'){
    const n=(c.hosts||[]).length;
    (c.hosts||[]).forEach(h=>bldCondsOnto(h,c.conds,c.mode));
    toast(ttN(c.mode==='add'?'buildings.bulk_added_to_units':'buildings.bulk_set_on_units',n,{clause:bldClauseText(c.conds)||tt('buildings.no_requirements')}),4200);
  }else if(c.kind==='upgrade'){
    const lv=b.work.levels[b.lvl],i=c.host.upgIndex;
    const clause=bldClauseText(c.conds);
    (lv.upgConds=lv.upgConds||[])[i]=c.conds;
    // two spaces before `requires`, the way the real entries are written
    lv.upgrades[i]=bldUpgName(lv.upgrades[i])+(clause?'  requires '+clause:'');
  }else{
    c.host.conds=c.conds; c.host.condEdited=true;
    c.host.requires=bldClauseText(c.conds);
  }
  // …and the same on the way out - rebuilt from state, and not a building edit:
  // these pools are saved by the unit editor, through its own payload.
  if(c.kind==='edrec'){ b.clause=null; renderEditor(); return; }
  const unit=c.kind==='unit';
  bldClauseUnstash(); b.clause=null;
  if(unit){ bldUnitRender(); return; }   // its own screen, and not a building edit yet
  bldTouched();
}
function renderClauseDialog(){
  const b=state.bld,c=b.clause;
  const bulk=c.kind==='bulk',n=bulk?c.hosts.length:0;
  const what=bulk
    ? ttN('buildings.who_can_recruit_these_units_here',n)
    : c.kind==='level'
    ? `${tt('buildings.who_can_build')} <b>${esc(b.d.levels[b.lvl].label)}</b>`
    : c.kind==='upgrade'
    ? `${tt('buildings.who_upgrades_into')} <b>${esc(bldUpgName(
        b.work.levels[b.lvl].upgrades[c.host.upgIndex]))}</b>`
    : (c.unit?tt('buildings.who_can_recruit_here',{unit:esc(c.unit)})
             :tt('buildings.when_applies',{keyword:esc(c.host.keyword)}));
  document.getElementById('modal').innerHTML=`
    <h2>${tt('buildings.requirements',{what})}</h2>
    <div class="mbody">
      ${bulk?bldBulkClauseHead(c):''}
      <div class="condlist" id="condList"></div>
      <div class="brow" style="margin-top:8px">
        <select id="condAdd" style="flex:0 0 260px">
          <option value="">${tt('buildings.add_a_requirement')}</option>
          ${Object.keys(COND_LABEL).map(k=>`<option value="${k}">${esc(COND_LABEL[k])}</option>`).join('')}
        </select>
        <span class="count">${tt('buildings.terms_are_evaluated_left_to_right')}</span>
      </div>
      <div id="condOwn"></div>
      <div id="condGates"></div>
      <div class="bsec" style="margin-top:12px"><h4>${tt('buildings.written_as')}</h4>
        <div class="preview" id="condText"></div></div>
    </div>
    <div class="foot">
      <button onclick="bldClauseCancel()">${tt('common.cancel')}</button>
      <button class="primary" onclick="bldClauseApply()">${bulk
        ? ttN('buildings.use_on_units',n) : tt('buildings.use_these_requirements')}</button>
    </div>`;
  document.getElementById('condAdd').onchange=e=>{
    if(!e.target.value)return;
    bldCondAdd(e.target.value); e.target.value='';
  };
  renderCondList();
}
/* The head of the bulk clause dialog: who it will land on, and whether it
   replaces what they say or is added to it. Replace is the default when they all
   already agree - you are narrowing one shared clause. When they disagree the
   dialog opens empty and defaults to ADD, because replacing a clause you were
   never shown is how a level quietly stops training half its units. */
function bldBulkClauseHead(c){
  const names=c.units.slice(0,14).map(esc);
  return `<div class="ownwarn" style="margin:0 0 10px">
    ${ttN('buildings.recruit_pools_named',c.hosts.length,{names:names.join('</code> <code>'),more:c.units.length>names.length?` <span class="count">${tt('buildings.more',{n:c.units.length-names.length})}</span>`:''})}
    <div class="brow" style="margin:7px 0 0">
      <label class="chk"><input type="radio" name="bulkmode" value="replace"
        ${c.mode!=='add'?'checked':''} onchange="bldClauseMode('replace')">
        ${tt('buildings.replace_what_each_of_them_requires')}</label>
      <label class="chk"><input type="radio" name="bulkmode" value="add"
        ${c.mode==='add'?'checked':''} onchange="bldClauseMode('add')">
        ${tt('buildings.add_these_terms_to_what_they')}</label>
    </div>
    <div class="count" style="margin-top:4px">${c.same
      ? tt('buildings.they_all_require_the_same_thing')
      : `${tt('buildings.they_do_not_all_require_the')} `}${
      c.mode==='add'
      ? tt('buildings.each_term_anded_onto_clause')
      : tt('buildings.replacing_throws_away_whatever_each_of')}</div>
  </div>`;
}
function bldCondAdd(kind){
  const c=state.bld.clause;
  const blank={factions:[],hidden_resource:[''],resource:[''],event_counter:['','1'],
    region_religion:['',''],building_present_min_level:['',''],building_present:[''],
    settlement_min:[''],market_level:['1'],raw:[]};
  c.conds.push({join:c.conds.length?'and':'',negate:false,kind,
                values:(blank[kind]||[]).slice(),raw:''});
  renderCondList();
}
function renderCondList(){
  const c=state.bld.clause;
  const box=document.getElementById('condList');
  box.innerHTML=c.conds.length?c.conds.map(condRowHtml).join('')
    :`<div class="condrow"><span class="count">${tt('buildings.no_requirements_anyone_always')}</span></div>`;
  document.getElementById('condText').textContent=bldClauseText(c.conds)||tt('buildings.no_requires_clause');
  wireCondRows();
  bldClauseOwnership();
  bldGatePaint();
}
function condRowHtml(cond,i){
  const v=cond.values||[];
  let body='';
  switch(cond.kind){
    case 'factions': body=condFactionsHtml(cond,i); break;
    case 'event_counter': body=
      condPick(i,0,'event',v[0])+
      `<select data-cv="${i}:1" style="flex:0 0 150px">
        <option value="1" ${v[1]!=='0'?'selected':''}>${tt('buildings.has_happened_1')}</option>
        <option value="0" ${v[1]==='0'?'selected':''}>${tt('buildings.has_not_happened_0')}</option></select>`;
      break;
    case 'region_religion': body=
      condPick(i,0,'religion',v[0])
      +qm(tt('buildings.minimum_percentage_of_the_region_that'),tt('buildings.minimum'))
      +`<input data-cv="${i}:1" value="${esc(v[1]||'')}" inputmode="numeric"
        style="flex:0 0 90px" placeholder="%">`;
      break;
    case 'hidden_resource':
      body=condPick(i,0,'hidden_resource',v[0])+condWhereHtml('hidden_resource',v[0]); break;
    case 'resource':
      body=condPick(i,0,'resource',v[0])+condWhereHtml('resource',v[0]); break;
    case 'building_present': body=condPick(i,0,'building',v[0]); break;
    case 'building_present_min_level':
      body=condPick(i,0,'building',v[0])+condPick(i,1,'level',v[1],v[0]); break;
    case 'settlement_min': body=condPick(i,0,'settlement',v[0]); break;
    case 'raw': body=`<input data-craw="${i}" value="${esc(cond.raw||'')}"
      style="flex:1" placeholder="${ttA('buildings.written_into_the_clause_exactly_as')}">`; break;
    default: body=`<input data-cv="${i}:0" value="${esc(v[0]||'')}" style="flex:1">`;
  }
  return `<div class="condrow" data-cond="${i}">
    ${i?`<select data-cjoin="${i}" class="cjoin">
        <option value="and" ${cond.join!=='or'?'selected':''}>${tt('buildings.and')}</option>
        <option value="or" ${cond.join==='or'?'selected':''}>${tt('buildings.or')}</option></select>`
      :`<span class="cjoin lead">${tt('buildings.if')}</span>`}
    <label class="chk">${qm(tt('buildings.invert_this_term_it_holds_when'),'not')}<input
      type="checkbox" data-cneg="${i}" ${cond.negate?'checked':''}> ${tt('common.not')}</label>
    <span class="ckind">${qm(bldCondKindHelp(cond.kind)||tt('buildings.a_term_of_the_requires_clause'),
      COND_LABEL[cond.kind]||cond.kind)}${esc(COND_LABEL[cond.kind]||cond.kind)}</span>
    ${body}
    <button class="x danger" onclick="bldCondRemove(${i})" title="${ttA('buildings.remove_this_requirement')}">🗑</button>
  </div>`;
}
function bldCondKindHelp(kind){
  const k=((state.bld.ov.condition_kinds)||[]).find(x=>x.kind===kind);
  return k&&k.help?k.help:'';
}
// A single-select over one of the mod's own lists. A text box with a suggestion
// list rather than a <select> because some of these lists run to two thousand
// entries (DaC declares 1 700 event counters) and a plain dropdown is unusable
// at that size. It was a <datalist> until a tester typed "Harad": see acAttach.
function condPick(i,slot,list,value,dep){
  return `<span class="acwrap" style="flex:1;min-width:110px"><input data-cv="${i}:${slot}"
      data-ac="${esc(list)}" data-acdep="${esc(dep||'')}" value="${esc(value||'')}"
      placeholder="${esc(list.replace('_',' '))}…"></span>`;
}
function condOptions(list,dep){
  const v=bldVocab();
  switch(list){
    case 'event': return (v.events||[]).map(e=>({value:e.name,
      label:(e.title?e.title+'. ':'')+(e.source==='edb'?tt('buildings.used_in_this_edb')
        :e.source==='script'?tt('buildings.set_by_a_script'):tt('buildings.from_historic_events_txt'))}));
    // Each of these means "the regions where it holds", so descr_regions.txt is
    // what the picker shows - a bare code name says nothing about where it bites.
    case 'religion': return (v.religion_rows||(v.religions||[]).map(r=>({code:r})))
      .map(r=>({value:r.code,label:r.regions
        ? ttN('buildings.regions_follow_it_up_to',r.regions,{max:r.max})
        : tt('buildings.no_region_follows_this')}));
    case 'hidden_resource': return (v.hidden_resources||[]).map(r=>({value:r.code,
      label:r.count?ttN('buildings.regions_listed',r.count,{regions:r.regions.slice(0,4).join(', '),more:r.regions.length>4?'…':''}):tt('buildings.no_region_carries_this')}));
    case 'resource': return (v.resources||[]).map(r=>({value:r.code||r,
      label:r.count?ttN('buildings.regions_listed',r.count,{regions:r.regions.slice(0,4).join(', '),more:r.regions.length>4?'…':''}):tt('buildings.not_placed_in_any_region')}));
    case 'settlement': return (state.bld.ov.settlement_levels||[]).map(s=>({value:s,label:s}));
    case 'building': return (v.building_levels||[]).map(b=>({value:b.line,
      label:ttN('buildings.level_count',b.levels.length)}));
    case 'level':{
      const line=(v.building_levels||[]).find(b=>b.line===dep);
      return (line?line.levels:[]).map(l=>({value:l,label:l}));}
  }
  return [];
}
/* ---- where a resource actually is ----
   `requires hidden_resource Arthedain` says nothing about where it bites: the
   name is invented by the mod and only means the handful of regions that carry
   it, out of descr_regions.txt. So the picker gets a marker that names the
   SETTLEMENTS on hover - the thing you recognise on the campaign map - with the
   region and its starting owner beside each. */
function condPlaces(kind,code){
  const v=bldVocab();
  const rows=(kind==='hidden_resource'?v.hidden_resources:v.resources)||[];
  // case-blind, as the engine is: `Resl` in a clause is the `ResL` a region carries
  const key=String(code||'').toLowerCase();
  const r=rows.find(x=>String(x.code||x).toLowerCase()===key);
  return (r&&r.places)||[];
}
// The owner's in-game name if the mod gave it one, else its code.
function condOwnerName(code){
  const f=(bldVocab().factions||[]).find(x=>x.code===code);
  return (f&&f.name)||code;
}
function condWhereHtml(kind,code){
  if(!code)return '';
  const places=condPlaces(kind,code);
  if(!places.length)return `<span class="where none" data-where="${esc(kind)}"
    title="${ttA('buildings.no_region_in_descr_regions_txt')}"
    >${tt('buildings.nowhere')}</span>`;
  const rows=places.map(p=>`<div class="wrow"><b>${esc(p.settlement)}</b>
      <span>${esc(p.region)}</span>
      ${p.faction?`<i>${esc(condOwnerName(p.faction))}</i>`:''}</div>`).join('');
  return `<span class="where" data-where="${esc(kind)}">${ttN('buildings.places_count',places.length)}
    <span class="wpop"><div class="whead">${tt('buildings.from_world_maps_base_descr_regions',{code:esc(code)})}</div>${rows}</span></span>`;
}
/* ---- every gate at once (Phase 51) ----
   Each resource term has its own "📍 N settlements", and nothing combined them:
   a pool gated on `hidden_resource GondorEast and hidden_resource ResF` meant
   working the overlap out by hand, and an overlap of nothing is a pool nobody
   can ever recruit from - the same silent failure as a missing resource.

   Only two kinds of term are a fact about a REGION that the files settle:
   `hidden_resource` and `resource`, off descr_regions.txt. Everything else -
   who owns it, an event, the religion it has drifted to, what is built there -
   is decided during play, so it does not narrow the list. It is evaluated as
   holding, and named under the result as an assumption, so the number is read
   as "the regions these gates allow" and never as more than that. Factions are
   SHOWN instead: each region carries its starting owner, and the ones a
   faction in the clause starts with are marked.

   Left to right, with no precedence, the way the engine reads a clause (the
   dialog already says so): `a or b and c` is `(a or b) and c`. */
const BLD_GATE_KINDS=new Set(['hidden_resource','resource']);
// true/false for a term the region's own lines decide, null for any other
function bldGateTerm(c,r){
  if(!c||!BLD_GATE_KINDS.has(c.kind))return null;
  const code=String((c.values||[])[0]||'').trim().toLowerCase();
  if(!code)return null;
  const list=(c.kind==='hidden_resource'?r.hidden_resources:r.resources)||[];
  const has=list.some(x=>String(x).toLowerCase()===code);
  return c.negate?!has:has;
}
function bldGateEval(conds,regions){
  conds=conds||[];
  const decides=c=>BLD_GATE_KINDS.has(c.kind)&&String((c.values||[])[0]||'').trim();
  if(!conds.some(decides))return null;          // nothing here is about a region
  const pass=(regions||[]).filter(r=>{
    let acc=true;
    conds.forEach((c,i)=>{
      const t=bldGateTerm(c,r);
      const v=t===null?true:t;
      acc=i===0?v:((c.join||'and')==='or'?(acc||v):(acc&&v));
    });
    return acc;
  });
  return {pass,total:(regions||[]).length,assumed:conds.filter(c=>!decides(c))};
}
// The factions a clause names, cultures and `all` expanded to real factions.
function bldGateFactions(conds){
  const v=bldVocab(),rows=v.factions||[],all=v.all_keyword||'all';
  const out=new Set();
  (conds||[]).filter(c=>c.kind==='factions'&&!c.negate).forEach(c=>
    (c.values||[]).forEach(x=>{
      if(x===all)return;                        // everyone: nothing to mark
      const members=rows.filter(f=>f.culture===x).map(f=>f.code);
      (members.length?members:[x]).forEach(m=>out.add(m));
    }));
  return out;
}
function bldGateRowsHtml(g,conds){
  const mine=bldGateFactions(conds);
  return g.pass.map(r=>`<div class="wrow${mine.has(r.faction)?' own':''}"><b>${esc(r.settlement_name||r.settlement)}</b>
      <span>${esc(r.name||r.region)}</span>
      ${r.faction?`<i>${esc(condOwnerName(r.faction))}${mine.has(r.faction)?' ★':''}</i>`:''}</div>`).join('');
}
function bldGateAssumedText(g){
  return g.assumed.map(bldCondSummary).join(', ');
}
// The chip on a row: nothing when no term is about a region.
function bldGateChip(conds){
  const g=bldGateEval(conds,bldVocab().regions);
  if(!g)return '';
  if(!g.pass.length)return `<span class="where none gate" title="${ttA('buildings.no_region_in_descr_regions_txt_2')}">${tt('buildings.no_region_passes_every_gate')}</span>`;
  return `<span class="where gate">${ttN('buildings.regions_pass',g.pass.length)}
    <span class="wpop"><div class="whead">${tt('buildings.every_resource_gate_at_once_from',{assumed:g.assumed.length
        ?`<br>${tt('buildings.assuming',{bldGateAssumedText:esc(bldGateAssumedText(g))})}`:''})}</div>${bldGateRowsHtml(g,conds)}</span></span>`;
}
// The dialog's box, redrawn as the terms change.
function bldGatePaint(){
  const box=document.getElementById('condGates'),c=state.bld&&state.bld.clause;
  if(!box||!c)return;
  const g=bldGateEval(c.conds,bldVocab().regions);
  if(!g){ box.innerHTML=''; return; }
  const mine=bldGateFactions(c.conds);
  const owned=g.pass.filter(r=>mine.has(r.faction)).length;
  box.innerHTML=`<div class="bsec gatebox ${foldCls('bld.gates')}" data-fold="bld.gates" style="margin-top:12px"><h4>${tt('buildings.every_gate_at_once_of_regions',{pass_n:g.pass.length,total:g.total})}</h4>
    ${g.pass.length
      ?`<div class="gaterows">${bldGateRowsHtml(g,c.conds)}</div>`
      :`<div class="w-bad">${tt('buildings.no_region_carries_every_resource_this')}</div>`}
    ${mine.size&&g.pass.length?`<div class="count">${tt('buildings.of_them_start_owned_by_a',{owned})}</div>`:''}
    ${g.assumed.length?`<div class="count">${tt('buildings.not_narrowed_by_because_the_files',{bldGateAssumedText:esc(bldGateAssumedText(g))})}</div>`:''}</div>`;
}
function condFactionsHtml(cond,i){
  const chosen=cond.values||[];
  const label=chosen.length?chosen.map(bldFacName).join(', '):tt('buildings.nobody_so_this_can_never_be');
  return `<button class="facbtn" onclick="bldFacPicker(${i})"
      title="${ttA('buildings.pick_the_factions_and_cultures_this')}">
      ${chosen.length?esc(label):'<span class="w-bad">'+esc(label)+'</span>'}</button>`;
}
function wireCondRows(){
  const c=state.bld.clause;
  document.querySelectorAll('[data-cjoin]').forEach(el=>el.onchange=()=>{
    c.conds[+el.dataset.cjoin].join=el.value; condChanged();});
  document.querySelectorAll('[data-cneg]').forEach(el=>el.onchange=()=>{
    c.conds[+el.dataset.cneg].negate=el.checked; condChanged();});
  document.querySelectorAll('[data-craw]').forEach(el=>el.oninput=()=>{
    c.conds[+el.dataset.craw].raw=el.value; condChanged();});
  document.querySelectorAll('[data-cv]').forEach(el=>{
    const [i,slot]=el.dataset.cv.split(':').map(Number);
    if(el.dataset.ac)acAttach(el,()=>condOptions(el.dataset.ac,el.dataset.acdep));
    const set=()=>{const cond=c.conds[i];
      while(cond.values.length<=slot)cond.values.push('');
      cond.values[slot]=el.value.trim();
      // the level list depends on which building line is picked
      if(cond.kind==='building_present_min_level'&&slot===0)renderCondList();
      else condChanged();};
    el.onchange=set; el.oninput=()=>{const cond=c.conds[i];
      while(cond.values.length<=slot)cond.values.push('');
      cond.values[slot]=el.value.trim();
      // keep "📍 8 settlements" in step with the resource being typed
      if(slot===0&&(cond.kind==='hidden_resource'||cond.kind==='resource')){
        const row=el.closest('.condrow'),old=row&&row.querySelector('[data-where]');
        const html=condWhereHtml(cond.kind,cond.values[0]);
        if(old)old.outerHTML=html; else if(row&&html)(el.closest('.acwrap')||el).insertAdjacentHTML('afterend',html);
      }
      condChanged();};
  });
}
function condChanged(){
  const c=state.bld.clause;
  document.getElementById('condText').textContent=bldClauseText(c.conds)||tt('buildings.no_requires_clause');
  bldClauseOwnership();
  bldGatePaint();
}
function bldCondRemove(i){
  const c=state.bld.clause;
  c.conds.splice(i,1);
  if(c.conds.length)c.conds[0].join='';
  renderCondList();
}

/* ---- the faction checklist ---- */
function bldFacPicker(i){
  const b=state.bld,c=b.clause;
  c.pick={i,q:''};
  b.stashScroll2=stashPlace();
  b.stash2=document.getElementById('modal').innerHTML;
  renderFacPicker();
}
function renderFacPicker(){
  const c=state.bld.clause,v=bldVocab();
  const cond=c.conds[c.pick.i],chosen=new Set(cond.values||[]);
  // what this condition named when the dialog opened, so a row you have since
  // ticked or unticked is marked as yours
  const was=new Set((((c.was||[])[c.pick.i])||{}).values||[]);
  const edited=code=>chosen.has(code)!==was.has(code);
  const ALL=v.all_keyword||'all';
  const q=(c.pick.q||'').toLowerCase();
  const match=r=>!q||r.code.toLowerCase().includes(q)||(r.name||'').toLowerCase().includes(q);
  const row=(r,isCulture)=>`<label class="facrow${chosen.has(r.code)?' on':''}${
        edited(r.code)?' edited':''}">
      <input type="checkbox" data-fac="${esc(r.code)}" ${chosen.has(r.code)?'checked':''}>
      <span class="fn">${esc(r.name||r.code)}</span>
      <span class="fc">${esc(r.code)}${isCulture?tt('buildings.culture_2'):r.culture?' · '+esc(r.culture):''}${
        edited(r.code)?(chosen.has(r.code)?tt('buildings.added_by_you'):tt('buildings.removed_by_you')):''}</span>
    </label>`;
  document.getElementById('modal').innerHTML=`
    <h2>${tt('buildings.which_factions')}</h2>
    <div class="mbody">
      <div class="brow"><input id="facQ" placeholder="${ttA('buildings.filter_by_name_or_code')}" style="flex:1"
        value="${esc(c.pick.q||'')}">
        <button onclick="bldFacAll(true)">${tt('buildings.tick_all_shown_2')}</button>
        <button onclick="bldFacAll(false)">${tt('buildings.untick_all_shown')}</button></div>
      <label class="facrow allrow${chosen.has(ALL)?' on':''}${edited(ALL)?' edited':''}">
        <input type="checkbox" data-fac="${esc(ALL)}" ${chosen.has(ALL)?'checked':''}>
        ${tt('buildings.all_factions_the_wildcard_ticking_it',{ALL:esc(ALL)})}</label>
      <h4 class="fgh">${tt('common.factions')}</h4>
      <div class="faclist">${(v.factions||[]).filter(match).map(r=>row(r,false)).join('')
        ||`<span class="count">${tt('buildings.none_match')}</span>`}</div>
      <h4 class="fgh">${tt('buildings.cultures_covers_every_faction_of_that')}</h4>
      <div class="faclist">${(v.cultures||[]).filter(match).map(r=>row(r,true)).join('')
        ||`<span class="count">${tt('buildings.none_match')}</span>`}</div>
      <div id="facOwn"></div>
    </div>
    <div class="foot">
      <span class="count" id="facCount"></span>
      <button class="primary" onclick="bldFacDone()">${tt('buildings.done')}</button>
    </div>`;
  const qbox=document.getElementById('facQ');
  qbox.oninput=()=>{c.pick.q=qbox.value;renderFacPicker();
    const n=document.getElementById('facQ');n.focus();n.setSelectionRange(n.value.length,n.value.length);};
  document.querySelectorAll('[data-fac]').forEach(cb=>cb.onchange=()=>{
    const set=new Set(cond.values||[]);
    cb.checked?set.add(cb.dataset.fac):set.delete(cb.dataset.fac);
    cond.values=[...set];
    renderFacPicker();});
  document.getElementById('facCount').textContent=
    `${(cond.values||[]).length} selected`;
  bldFacOwnership(cond.values||[]);
}
function bldFacAll(on){
  const c=state.bld.clause,cond=c.conds[c.pick.i];
  const set=new Set(cond.values||[]);
  document.querySelectorAll('[data-fac]').forEach(cb=>{
    if(cb.closest('.allrow'))return;         // never bulk-tick the wildcard
    on?set.add(cb.dataset.fac):set.delete(cb.dataset.fac);});
  cond.values=[...set];
  renderFacPicker();
}
function bldFacDone(){
  const b=state.bld;
  document.getElementById('modal').innerHTML=b.stash2; b.stash2=null;
  b.clause.pick=null;
  usePlace(b.stashScroll2); b.stashScroll2=null;
  renderClauseDialog();
}

/* ---- "…but this unit doesn't belong to them" ----
   A recruit_pool naming a faction is only half of it: the unit must also list
   that faction in its EDU `ownership`, and its battle model needs a texture for
   it, or the building trains nothing / trains something untextured. Both fail
   silently in game, so they are checked as soon as a faction is ticked. */
async function bldOwnCheck(unit,factions){
  return (await bldOwnChecks([unit],factions))[0]||null;
}
// The same question for a whole bulk selection, asked in ONE request: the
// endpoint already takes a list of checks, and a hundred round trips for a
// hundred ticked units is a hundred round trips.
async function bldOwnChecks(units,factions){
  const b=state.bld,facs=[...factions].sort();
  const key=u=>u+'|'+facs.join(',');
  const want=[...new Set(units)].filter(u=>u&&!(key(u) in b.own));
  if(want.length){
    try{
      const r=await api.post('/api/buildings/ownership',
        {mod:b.mod,checks:want.map(u=>({unit:u,factions:facs}))});
      const rows=r.rows||[];
      want.forEach((u,i)=>{ b.own[key(u)]=rows[i]||null; });
    }catch(e){ want.forEach(u=>{ b.own[key(u)]=null; }); }
  }
  return [...new Set(units)].map(u=>b.own[key(u)]).filter(Boolean);
}
function bldOwnHtml(row){
  if(!row)return '';
  if(!row.known)return `<div class="ownwarn bad">${tt('buildings.is_not_a_unit_in_this',{unit:esc(row.unit)})}</div>`;
  const bits=[],fixes=[];
  if(row.missing_ownership.length){
    bits.push(ttN('buildings.factions_not_in_unit_ownership',row.missing_ownership.length,{factions:row.missing_ownership.map(bldFacName).map(esc).join(', '),unit:esc(row.unit)}));
    fixes.push(tt('buildings.the_ownership_line_is_extended'));
  }
  if(row.missing_textures.length){
    bits.push(tt('buildings.its_battle_model_has_no_texture',{x:row.missing_textures.map(esc).join(', ')}));
    fixes.push(tt('buildings.the_missing_textures_are_copied_from'));
  }
  if(!bits.length)return `<div class="ownwarn ok">${tt('buildings.every_faction_here_can_already_field',{unit:esc(row.unit)})}</div>`;
  return `<div class="ownwarn">${ttN('buildings.saving_fixes_these',bits.length,{bits:bits.join('; and '),fixes:fixes.join(', and ')})}</div>`;
}
// Over many units the individual warnings would be a wall of text, so they are
// rolled into one line per problem naming the units - the answer you want is
// "which of these twelve can't the Danes actually field", not twelve paragraphs.
function bldOwnManyHtml(rows){
  const bad=rows.filter(r=>r&&(!r.known||r.missing_ownership.length||r.missing_textures.length));
  if(!rows.length)return '';
  if(!bad.length)return `<div class="ownwarn ok">${tt('buildings.every_faction_here_can_already_field_2',{rows_n:rows.length})}</div>`;
  if(bad.length===1&&rows.length===1)return bldOwnHtml(bad[0]);
  const unknown=bad.filter(r=>!r.known).map(r=>r.unit);
  const noOwn=bad.filter(r=>r.known&&r.missing_ownership.length);
  const noTex=bad.filter(r=>r.known&&r.missing_textures.length);
  const list=us=>`<code>${us.slice(0,12).map(esc).join('</code> <code>')}</code>${
    us.length>12?` <span class="count">${tt('buildings.more_2',{us:us.length-12})}</span>`:''}`;
  const bits=[];
  if(unknown.length)bits.push(`<div>${ttN('buildings.units_not_in_this_mods_edu',unknown.length,{list:list(unknown)})}</div>`);
  if(noOwn.length)bits.push(`<div>${ttN('buildings.units_not_listing_every_faction',noOwn.length,{list:list(noOwn.map(r=>r.unit))})}</div>`);
  if(noTex.length)bits.push(`<div>${ttN('buildings.units_without_battle_model_texture',noTex.length,{list:list(noTex.map(r=>r.unit))})}</div>`);
  return `<div class="ownwarn ${unknown.length?'bad':''}">${bits.join('')}
    <div class="count" style="margin-top:5px">${docPoints(
      tt('buildings.saving_fixes_the_ownership_and_copies'),[
      tt('buildings.untick_fix_unit_ownership_at_the'),
      tt('buildings.a_unit_the_edu_doesnt_have')])}</div></div>`;
}
async function bldOwnBox(id,facs){
  const c=state.bld.clause;
  const units=(c&&(c.units&&c.units.length?c.units:(c.unit?[c.unit]:[])))||[];
  if(!units.length)return;
  const box=document.getElementById(id);
  if(!box)return;
  if(!facs.length){box.innerHTML='';return;}
  const rows=await bldOwnChecks(units,facs);
  // the dialog may have moved on while the request was out
  if(state.bld.clause!==c)return;
  box.innerHTML=units.length===1?bldOwnHtml(rows[0]):bldOwnManyHtml(rows);
}
async function bldClauseOwnership(){
  const c=state.bld.clause; if(!c)return;
  const facs=[].concat(...c.conds.filter(x=>x.kind==='factions'&&!x.negate)
    .map(x=>x.values||[]));
  return bldOwnBox('condOwn',facs);
}
async function bldFacOwnership(facs){ return bldOwnBox('facOwn',facs); }

/* ---- add units to this level's recruitment ----
   A level is filled out a dozen units at a time, not one, so the picker TICKS
   rather than adds: a row you tick stays ticked while you keep filtering, and
   one button adds the lot. The count in the button is the whole selection, not
   just what the current filter shows. */
function bldAddPoolDialog(){
  const b=state.bld,lv=b.work.levels[b.lvl];
  const already=new Set([...lv.caps,...lv.fcaps].filter(c=>c.pool&&!c.del)
    .map(c=>c.pool.unit.toLowerCase()));
  const above=b.work.levels.length-1-b.lvl, twin=bldTwin(), twinLv=bldTwinLevel();
  // The numbers used to be fixed and invisible, so every added unit had to be
  // corrected row by row afterwards. They are the dialog's own fields now, and
  // they carry over to the tiers above with a per-tier step.
  b.pick={q:'',faction:'',already,picked:new Set(),
          nums:{initial:'1',per_turn:'0.5',maximum:'2',experience:'0'},
          tiers:false,bump:Object.assign({},BLD_TIER_BUMP),mirror:false,
          // the row whose `＋` opened this, if one did: the new rows go under it
          after:b.insertAfter||null};
  b.insertAfter=null;
  const modal=document.getElementById('modal');
  b.stashScroll=stashPlace();
  b.stash=modal.innerHTML;                     // put the editor back on cancel
  modal.innerHTML=`<h2>${tt('buildings.add_units_to',{x:esc(b.d.levels[b.lvl].label)})}</h2>
    <div class="mbody">
      <div class="basebar"><input id="bpQ" placeholder="${ttA('buildings.filter_s_units',{src:esc(state.src)})}"
          oninput="bldPickFilter()"><select id="bpFac" onchange="bldPickFilter()">
          <option value="">${tt('common.all_factions')}</option>${
            (state.data.factions||[]).slice().sort((a,c)=>facLabel(a).localeCompare(facLabel(c)))
              .map(f=>`<option value="${esc(f)}">${esc(facLabel(f))}</option>`).join('')}
        </select>
        <button onclick="bldPickAll(true)">${tt('buildings.tick_all_shown_2')}</button>
        <button onclick="bldPickAll(false)">${tt('buildings.untick_all')}</button></div>
      <div class="baselist" style="max-height:260px" id="bpList"></div>

      <div class="bsec" style="margin-top:10px"><h4>${tt('buildings.numbers_each_new_pool_starts_with')}</h4>
        <div class="brow bpnums">
          <label>${qm(POOL_HELP.initial,POOL_LABEL.initial)}${POOL_LABEL.initial}${
            numBox('data-bp="initial"',b.pick.nums.initial,'pool')}</label>
          <label>${qm(POOL_HELP.per_turn,POOL_LABEL.per_turn)}${POOL_LABEL.per_turn}${
            numBox('data-bp="per_turn"',b.pick.nums.per_turn,'turns',
              `<span class="turns">= ${esc(poolTurns(b.pick.nums.per_turn))}</span>`)}</label>
          <label>${qm(POOL_HELP.maximum,POOL_LABEL.maximum)}${POOL_LABEL.maximum}${
            numBox('data-bp="maximum"',b.pick.nums.maximum,'pool')}</label>
          <label>${qm(POOL_HELP.experience,POOL_LABEL.experience)}${POOL_SHORT.experience}${
            numBox('data-bp="experience"',b.pick.nums.experience,'1')}</label>
        </div>

        ${above>0?`<label class="chk" title="${esc(bldTiersAboveNames())}">
          <input type="checkbox" id="bpTiers" onchange="bldPickOpt('tiers',this.checked)">
          ${tt('buildings.add_to_the_tier_s_above',{above})}
          <span class="count">${esc(bldTiersAboveNames())}</span></label>
        <div class="brow bpnums" id="bpBump" style="display:none">
          <span class="k">${tt('buildings.each_tier_up_by')}</span>
          <label>${POOL_LABEL.initial}${numBox('data-bpb="initial"',b.pick.bump.initial,'1')}</label>
          <label>${POOL_LABEL.per_turn}${numBox('data-bpb="per_turn"',b.pick.bump.per_turn,'0.05')}</label>
          <label>${POOL_LABEL.maximum}${numBox('data-bpb="maximum"',b.pick.bump.maximum,'1')}</label>
          <label>${POOL_SHORT.experience}${numBox('data-bpb="experience"',b.pick.bump.experience,'1')}</label>
        </div>`
        :`<div class="bnote">${tt('buildings.this_is_the_top_tier_so')}</div>`}

        ${twin&&twinLv?`<label class="chk"><input type="checkbox" id="bpMirror"
            onchange="bldPickOpt('mirror',this.checked)">
          ${tt('buildings.mirror_into_the_half_of_this',{twin:esc(twin),twinLv:esc(twinLv),settlement:esc(b.d.settlement==='city'?'castle':'city')})}</label>`
        :`<div class="bnote">${tt('buildings.no_city_castle_twin_the_tool')}</div>`}
      </div>

      <div class="bnote">${docPoints(tt('buildings.new_pool_gated_to_ownership'),[
        tt('buildings.open_requirements_on_the_row_to'),
        tt('buildings.or_tick_several_rows_and_use')])}</div>
    </div>
    <div class="foot"><span class="count" id="bpCount"></span>
      <button onclick="bldPickCancel()">${tt('common.cancel')}</button>
      <button class="primary" id="bpAdd" onclick="bldAddPicked()">${tt('common.add_2')}</button></div>`;
  wireNumBoxes(modal);
  modal.querySelectorAll('[data-bp],[data-bpb]').forEach(inp=>{
    const bump=inp.dataset.bpb!==undefined;
    inp.addEventListener('input',()=>{
      (bump?b.pick.bump:b.pick.nums)[bump?inp.dataset.bpb:inp.dataset.bp]=inp.value;
    });
  });
  bldPickRender();
}
function bldPickOpt(key,on){
  state.bld.pick[key]=on;
  const box=document.getElementById('bpBump');
  if(box&&key==='tiers')box.style.display=on?'':'none';
  bldPickRender();
}
// Shared by the add-unit picker and the cross-tree compare panel: both stash the
// editor's markup on the way in and hand it back here.
function bldPickCancel(){
  const modal=document.getElementById('modal');
  modal.innerHTML=state.bld.stash; state.bld.stash=null; state.bld.cmp=null;
  state.bld.vc=null;
  usePlace(state.bld.stashScroll); state.bld.stashScroll=null;
  bldRedrawLevel();
}
// The rows the filter boxes are letting through right now.
function bldPickShown(){
  const p=state.bld.pick;
  return (state.data.units||[]).filter(u=>
    (!p.q||u.name.toLowerCase().includes(p.q)||u.type.toLowerCase().includes(p.q))
    &&(!p.faction||u.ownership.includes(p.faction))).slice(0,300);
}
function bldPickFilter(){
  const p=state.bld.pick;
  p.q=(document.getElementById('bpQ').value||'').trim().toLowerCase();
  p.faction=document.getElementById('bpFac').value;
  bldPickRender();
}
function bldPickToggle(type){
  const p=state.bld.pick;
  p.picked.has(type)?p.picked.delete(type):p.picked.add(type);
  bldPickRender();
}
function bldPickAll(on){
  const p=state.bld.pick;
  bldPickShown().forEach(u=>on?p.picked.add(u.type):p.picked.delete(u.type));
  bldPickRender();
}
function bldPickRender(){
  const p=state.bld.pick,already=p.already;
  const units=bldPickShown();
  document.getElementById('bpList').innerHTML=units.map(u=>`
    <div class="baserow ${p.picked.has(u.type)?'on':''}" onclick="bldPickToggle('${q1(esc(u.type))}')">
      <label class="pick" onclick="event.preventDefault()"><input type="checkbox"
        ${p.picked.has(u.type)?'checked':''}></label>
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,u.type)}">
      <div><div class="bn">${esc(u.name)}${already.has(u.type.toLowerCase())
        ?` <span class="badge">${tt('buildings.already_here')}</span>`:''}</div>
        <div class="bs">${esc(u.type)} · ${esc(u.kind||u.category||'')}</div></div>
    </div>`).join('')||`<div class="caprow"><span class="count">${tt('common.no_units_match')}</span></div>`;
  const n=p.picked.size;
  const cnt=document.getElementById('bpCount');
  if(cnt)cnt.textContent=n?ttN(units.length<n?'buildings.count_ticked_some_outside':'buildings.count_ticked',n)
                          :tt('buildings.tick_the_units_to_add');
  const add=document.getElementById('bpAdd');
  if(add){add.textContent=n?ttN('buildings.add_units_count',n):tt('common.add_2');add.disabled=!n;}
}
/* A pool with no clause is trained by EVERY faction that can build the level,
   which is almost never what adding one unit means - and for the factions that
   don't own the unit the building silently trains nothing. So a new pool starts
   gated to the unit's own EDU `ownership`: the set that can actually field it.
   It is a starting point, not a rule - the row's Requirements button opens the
   clause like any other. A unit with no ownership gets no clause, because an
   empty `factions { }` would train nothing for anyone; the editor's existing
   "no ownership" warning is the thing to fix there. */
const bldPickedUnit=type=>(state.data.units||[]).find(x=>x.type===type);
function bldPoolOwnership(type){
  const u=bldPickedUnit(type);
  const own=[...new Set((u&&u.ownership)||[])];
  return own.length?[{join:'',negate:false,kind:'factions',values:own,raw:''}]:[];
}
// One new pool row, appended to the level. Returns it, so the caller can say
// what it did - nothing here touches the DOM, because adding twenty units must
// redraw once rather than twenty times.
function bldAddPoolRow(type,lvIndex,nums,conds){
  const b=state.bld,lv=b.work.levels[lvIndex==null?b.lvl:lvIndex];
  if(!lv)return null;
  // A copy of an existing pool brings that pool's own clause; a unit added from
  // the picker gets its EDU ownership instead (see bldPoolOwnership).
  const raw=(nums&&nums.requires!==undefined)?String(nums.requires||''):null;
  conds=conds||(raw===null?bldPoolOwnership(type):[]);
  // `d.units` only indexes the units this line ALREADY trains - the server sends
  // it once per line rather than the mod's whole EDU. A unit added here is by
  // definition not in it yet, so the row would call itself missing from the EDU
  // until the next save. It came out of the picker, which reads that same EDU.
  const u=bldPickedUnit(type);
  if(u&&b.d&&b.d.units&&!b.d.units[type.toLowerCase()])
    b.d.units[type.toLowerCase()]={type:u.type,name:u.name||u.type,kind:u.kind,
      class:u.class,category:u.category,ownership:[...(u.ownership||[])],
      mercenary:!!u.mercenary,eop:!!u.eop,missing:false};
  // A clause copied verbatim from another row goes back as its ORIGINAL text:
  // re-emitting it from structure would quietly re-tidy a clause nobody edited.
  const edited=raw===null||!!(conds&&conds.length);
  const row={line:null,keyword:'recruit_pool',args:'',
    requires:edited?bldClauseText(conds):raw,conds:conds||[],condEdited:edited,
    bonus:false,value:'',
    pool:Object.assign({unit:type,initial:'1',per_turn:'0.5',maximum:'2',experience:'0'},
                       nums?{initial:nums.initial,per_turn:nums.per_turn,
                             maximum:nums.maximum,experience:nums.experience}:{},
                       {unit:type}),
    comment:'',faction:false,del:false};
  /* At the END, because since Phase 51 the list's order is what gets written
     (buildings._plan_capabilities), and the end is where a new line has always
     gone in the file. These rows used to be shown at the TOP and written at the
     bottom, which is the "added units end up at the end with no way to move
     them" the 51 feedback was about. `bldAddPicked` scrolls to them, which is
     what showing them at the top was for, and `＋` on a row puts them under it.
     A batch keeps the order it was ticked in. */
  lv.caps.push(row);
  return row;
}
function bldAddPool(type){ bldAddPicked([type]); }
/* Commit the picker's ticks. The rows land ticked in bulk edit as well, because
   the thing you do straight after adding twelve units is give all twelve the
   same requires clause - and hunting them back down in a list of three hundred
   is exactly the work this is meant to save. */
function bldAddPicked(types){
  if(!foldIsOpen('bld.recruit'))foldSet('bld.recruit',true);
  const b=state.bld;
  const list=types||[...((b.pick&&b.pick.picked)||[])];
  if(!list.length)return;
  const p=b.pick||{};
  const nums=p.nums||{initial:'1',per_turn:'0.5',maximum:'2',experience:'0'};
  const rows=list.map(t=>bldAddPoolRow(t,b.lvl,nums));
  // opened from a row's `＋`: the batch goes directly under that row, in the
  // order it was ticked. Only inside the same block (see bldMoveCap).
  if(p.after&&!p.after.faction){
    const arr=b.work.levels[b.lvl].caps;
    let prev=p.after;
    rows.forEach(r=>{
      if(!arr.includes(prev))return;
      arr.splice(arr.indexOf(r),1);
      arr.splice(arr.indexOf(prev)+1,0,r);
      prev=r;
    });
  }
  // …and the same units into the tiers above and the twin building, on the same
  // clause each row just got, so one trip through the picker fills the chain
  let up=0,mirrored=0;
  if(p.tiers){
    for(let j=b.lvl+1;j<b.work.levels.length;j++){
      rows.forEach(r=>{
        if(bldHasUnit(j,r.pool.unit))return;
        bldAddPoolRow(r.pool.unit,j,bldBumped(r.pool,j-b.lvl,p.bump),
                      JSON.parse(JSON.stringify(r.conds||[])));
        up++;
      });
    }
  }
  if(p.mirror){
    const twin=bldTwin();
    for(let j=b.lvl;j<b.work.levels.length;j++){
      const tl=bldTwinLevel(j);
      if(!twin||!tl||(j>b.lvl&&!p.tiers))break;
      rows.forEach(r=>{
        const pool=j===b.lvl?r.pool:bldBumped(r.pool,j-b.lvl,p.bump);
        if(bldStagePool(twin,tl,Object.assign({},pool,{unit:r.pool.unit}),r.conds))mirrored++;
      });
    }
  }
  // A gated pool can fall outside the faction filter that is narrowing the list,
  // and a unit that vanishes the moment you add it looks like the add failed.
  if(rows.some(r=>!bldPoolMatches(r))&&b.poolFac)b.poolFac.clear();
  b.bulk=b.bulk||{sel:new Set()};
  b.bulk.on=true; b.bulk.sel=new Set(rows);
  // the picker replaced the editor's markup - rebuild it, then show the new rows
  const modal=document.getElementById('modal');
  if(b.stash){ modal.innerHTML=b.stash; b.stash=null; }
  usePlace(b.stashScroll); b.stashScroll=null;
  renderBuildingEditor();
  // the code view is re-rendered from the edits the way any other edit does
  // it; before Phase 51 this path skipped it and the pane went on showing the
  // level without the new rows until the next keystroke
  bldCvFollow();
  // …and bring the first one into view: the list can be eighty rows long
  const first=document.querySelector(`#bldBody [data-cap="${bldCapList().indexOf(rows[0])}"]`);
  if(first){ first.scrollIntoView({block:'center'}); first.classList.add('justadded'); }
  const label=b.d.levels[b.lvl].label;
  const gated=rows.filter(r=>r.conds.length).length;
  const extra=(up?tt('buildings.on_the_tier_s_above',{up}):'')
             +(mirrored?tt('buildings.staged_in',{mirrored,bldTwin:bldTwin()}):'');
  toast(rows.length===1
    ? tt('buildings.added_to_3',{list:list[0],label,x:rows[0].conds.length
        ? tt('buildings.restricted_to_its_owning_faction_s',{n:rows[0].conds[0].values.length})
        : tt('buildings.and_it_has_no_ownership_so'),extra})
    : tt('buildings.units_added_to_gated_to_their',{rows_n:rows.length,label,gated,x:gated<rows.length?tt('buildings.with_no_ownership_to_gate_to',{x:rows.length-gated}):'',extra}),4600);
}

/* =========================================================================
   Recruitment checks, mirroring and cross-tree editing

   Three things are invisible one level at a time and obvious across a whole
   line, and all three are mistakes a mod actually ships:

     * a unit recruitable at tier 2 that silently stops being recruitable when
       the player upgrades to tier 3 - the building "loses" units as it grows;
     * a unit the city half trains and the castle half does not, when the two are
       meant to be the same building;
     * the same unit listed twice in one level, which the game reads as two pools
       feeding one recruitment slot.

   The server works them out (buildings.line_checks); everything here is the
   panel that shows them and the one-click fixes. A fix never writes: it stages
   rows into the working copy exactly as adding a unit by hand does, so Probe,
   Save, Ctrl+Z and the log all behave the same.
   ========================================================================= */
async function bldLoadChecks(force){
  const b=state.bld,line=b&&b.line; if(!line)return;
  if(b.checks&&b.checks.line===line&&!force)return;
  try{
    const r=await api.get(`/api/buildings/checks?mod=${enc(b.mod)}&line=${enc(line)}`);
    if(state.bld!==b||b.line!==line)return;          // moved on while in flight
    b.checks=(r.lines||[])[0]||{line,gaps:[],dupes:[],mirror:[],level_pairs:{}};
    // 44: the tree findings for THIS line ride in the same answer, so the two
    // halves of "what is wrong with this building" land together
    b.lineTree=r.tree||null;
  }catch(e){ if(state.bld!==b||b.line!==line)return; b.checks={line,error:''+e}; }
  // The whole body, not just the panel: knowing the twin is what puts the ⇄
  // button on every pool row, and the answer only lands after the first draw.
  if(document.getElementById('bldChecks'))bldRenderBodyNow();
  // …and the header's "Compare city / castle" button, which cannot know whether
  // there IS a twin until this answer arrives.
  const btn=document.getElementById('bldVarBtn');
  if(btn)btn.innerHTML=bldVarBtnHtml();
}
// The twin line's name, and the level in it that mirrors the one on screen.
function bldTwin(){ return ((state.bld||{}).checks||{}).twin||''; }
function bldTwinLevel(i){
  const b=state.bld,ck=b.checks||{};
  const lv=b.work.levels[i==null?b.lvl:i];
  return lv?((ck.level_pairs||{})[lv.name]||''):'';
}
function bldChecksHtml(){
  return `<div class="bsec ${foldCls('bld.checks')}" data-fold="bld.checks" id="bldChecks">${
    bldChecksInner()}${bldTreeFindHtml()}</div>`;
}

/* =========================================================================
   44 - THE TREE'S FINDINGS.

   `bldChecksInner` above is about RECRUITMENT and this is about SHAPE, and
   they are two panels rather than one because they answer different questions:
   that one is read while editing a level's pools, this one while looking at
   whether the line hangs together at all.

   Both come out of the same request. Nothing here decides anything - the rules,
   their severities and their sentences are all `buildings.tree_check`'s, for
   20a's reason one screen further out: a rule written twice is two rules that
   will disagree.
   ========================================================================= */
const BLD_SEV={fatal:{cls:'w-bad', word:tt('buildings.must_fix')},
               warn:{cls:'w-warn', word:tt('buildings.worth_a_look')},
               note:{cls:'', word:tt('buildings.worth_knowing')}};

function bldFindRowsHtml(finds,withLine){
  return finds.map(f=>`<div class="ckrow">
    <div class="ckwho">
      <div class="un">${esc(f.message)}</div>
      <div class="ut"><code>${esc(f.code)}</code>${
        f.line?tt('buildings.edb_line',{line:f.line}):''}${
        withLine&&f.building?` · <code>${esc(f.building)}</code>`:''}</div>
    </div>${withLine&&f.building
      ? `<button onclick="openBuilding('${q1(esc(f.building))}')"
           title="${ttA('buildings.open_this_building_line_and_the')}">${tt('buildings.open')}</button>`
      : ''}</div>`).join('');
}

function bldTreeFindHtml(){
  const t=(state.bld||{}).lineTree;
  if(!t)return '';
  const f=t.findings||[];
  if(!f.length)return `<div class="bsec"><h4>${tt('buildings.the_tree_clean')}</h4>
    <div class="bnote">${tt('buildings.this_lines_name_is_its_own',{rules_n:t.rules.length})}</div></div>`;
  return `<div class="bsec"><h4>${ttN('buildings.the_tree_findings',f.length)}</h4>
    ${['fatal','warn','note'].filter(s=>f.some(x=>x.severity===s)).map(s=>`
      <div class="ckgroup"><div class="ckhead ${BLD_SEV[s].cls}">
        ${BLD_SEV[s].word} <span class="count">${
          f.filter(x=>x.severity===s).length}</span></div>
      <div class="cklist">${bldFindRowsHtml(f.filter(x=>x.severity===s),false)}</div>
      </div>`).join('')}</div>`;
}

/* ---- the same rules over the WHOLE file, on the mod's own screen ----

   The first half of M17: one door to a validator rather than a finding you only
   meet if you happen to open the building it is about. Fetched once per mod and
   only when the banner is opened, because it is a second request and most
   visits to this screen are to look at a building rather than to audit one. */
async function bldTreeChkLoad(force){
  const b=state.bld;
  if(!b)return;
  if(b.treeChk&&b.treeChkMod===b.mod&&!force)return;
  b.treeChkBusy=true; bldTreeChkPaint();
  try{
    const r=await api.get(`/api/buildings/checks?mod=${enc(b.mod)}`);
    if(state.bld!==b)return;
    b.treeChk=r.tree||{findings:[],counts:{},rules:[],refused:[]}; b.treeChkMod=b.mod;
  }catch(e){ if(state.bld===b)b.treeChk={error:errText(e),findings:[],rules:[],refused:[]}; }
  finally{ if(state.bld===b){ b.treeChkBusy=false; bldTreeChkPaint(); } }
}
function bldTreeChkToggle(){
  const b=state.bld; if(!b)return;
  b.treeChkOpen=!b.treeChkOpen;
  activity('buildings',b.treeChkOpen?tt('buildings.opened_the_edb_tree_check'):tt('common.closed_it'));
  if(b.treeChkOpen)bldTreeChkLoad(); else bldTreeChkPaint();
}
function bldTreeChkPaint(){
  const el=document.getElementById('bldTreeChk');
  if(el)el.innerHTML=bldTreeChkInner();
}
function bldTreeChkHtml(){
  return `<div id="bldTreeChk">${bldTreeChkInner()}</div>`;
}
//: "3 worth knowing", "2 must fix · 5 worth a look", or "clean". Joined rather
//: than concatenated with a separator per part, which left a trailing "·" on
//: any mod that had exactly one kind of finding - which is both of the ones
//: installed here.
function bldChkTally(c){
  const parts=[];
  if(c.fatal)parts.push(tt('buildings.must_fix_2',{fatal:c.fatal}));
  if(c.warn)parts.push(tt('buildings.worth_a_look_2',{warn:c.warn}));
  if(c.note)parts.push(tt('buildings.worth_knowing_2',{note:c.note}));
  return parts.length?parts.join(' · '):'clean';
}
function bldTreeChkInner(){
  const b=state.bld||{},t=b.treeChk;
  const head=`<button class="ckopen${b.treeChkOpen?' on':''}" onclick="bldTreeChkToggle()"
      title="${ttA('buildings.every_rule_over_the_shape_of')}">${tt('buildings.check_the_tree',{counts:t&&t.counts?` <span class="count">${esc(bldChkTally(t.counts))}</span>`:''})}</button>`;
  if(!b.treeChkOpen)return head;
  if(b.treeChkBusy)return `${head}<div class="bnote">${tt('buildings.reading_the_whole_file')}</div>`;
  if(!t)return head;
  if(t.error)return `${head}<div class="bnote w-bad">${esc(t.error)}</div>`;
  const f=t.findings||[];
  const body=!f.length
    ? `<div class="bnote">${tt('buildings.nothing_to_report_rules_ran_over',{rules_n:t.rules.length})}</div>`
    : ['fatal','warn','note'].filter(s=>f.some(x=>x.severity===s)).map(s=>`
        <div class="ckgroup"><div class="ckhead ${BLD_SEV[s].cls}">
          ${BLD_SEV[s].word} <span class="count">${
            f.filter(x=>x.severity===s).length}</span></div>
        <div class="cklist">${bldFindRowsHtml(f.filter(x=>x.severity===s),true)}</div>
        </div>`).join('');
  return `${head}<div class="bsec">${body}
    <details class="bnote"><summary>${tt('buildings.the_rules_and_the_three_that',{rules_n:t.rules.length})}</summary>
      <div class="cklist">${(t.rules||[]).map(r=>`<div class="ckrow">
        <div class="ckwho"><div class="un">${esc(r.label)}
          <span class="count">${esc(r.severity)}</span></div>
        <div class="ut"><code>${esc(r.code)}</code> · ${esc(r.source)}</div></div>
        </div>`).join('')}</div>
      <p><b>${tt('buildings.refused_each_for_a_measurement')}</b></p>
      <div class="cklist">${(t.refused||[]).map(x=>`<div class="ckrow">
        <div class="ckwho"><div class="un">${esc(x.rule)}</div>
        <div class="ut">${esc(x.measured)} <b>${esc(x.verdict)}</b></div></div>
        </div>`).join('')}</div>
    </details></div>`;
}
/* ---- the hidden_resources line (Phase 45) ----
   The list at the top of the EDB that every `requires hidden_resource X` names.
   It was read four ways and writable none: this adds a name and takes one off.
   Taking one off is the dangerous half - the provinces that carry the name and
   the clauses that gate on it all go dark in silence - so a removal first shows
   every one of them, and the server refuses it until the box saying so is
   ticked. The count sits beside the ceiling a wiki claims and the two mods here
   exceed, as information and never as a refusal. */
function bldHidToggle(){
  const b=state.bld; if(!b)return;
  b.hidOpen=!b.hidOpen;
  if(b.hidOpen&&(!b.hid||b.hid.mod!==b.mod))bldHidLoad(); else bldHidPaint();
}
async function bldHidLoad(){
  const b=state.bld;
  b.hid={mod:b.mod,busy:true,plan:null,pend:null,ack:false,add:''};
  bldHidPaint();
  let r;
  try{ r=await api.post('/api/buildings/hidden/plan',{mod:b.mod}); }
  catch(e){ r={error:errText(e)}; }
  if(state.bld!==b)return;
  b.hid.busy=false;
  b.hid.base=r.plan?r.plan.impact:null;
  b.hid.err=r.plan?'':(r.error||'');
  bldHidPaint();
}
function bldHidPaint(){
  const el=document.getElementById('bldHid');
  if(el)el.innerHTML=bldHidInner();
}
function bldHidHtml(){ return `<div id="bldHid">${bldHidInner()}</div>`; }
function bldHidInner(){
  const b=state.bld||{},h=b.hid;
  const n=((b.ov||{}).hidden_resources||[]).length;
  const head=`<button class="ckopen${b.hidOpen?' on':''}" onclick="bldHidToggle()"
      title="${ttA('buildings.the_hidden_resources_line_at_the')}">${tt('buildings.hidden_resources')}
      <span class="count">${n}</span></button>`;
  if(!b.hidOpen)return head;
  if(!h||h.busy)return `${head}<div class="bnote">${tt('buildings.reading_the_line_and_what_uses')}</div>`;
  if(h.err)return `${head}<div class="bnote w-bad">${esc(h.err)}</div>`;
  const base=h.base||{names:[]};
  const rows=base.names.map(x=>`<div class="hidrow${x.provinces||x.clauses?'':' unused'}">
      <b>${esc(x.name)}</b>
      <span class="count">${tt('buildings.provinces_and_clauses',{provinces:ttN('buildings.province_count',x.provinces),clauses:ttN('buildings.clause_count',x.clauses)})}</span>
      <button class="x danger" onclick="bldHidAsk('remove','${q1(esc(x.name))}')"
        title="${ttA('buildings.take_off_the_line_shows_what',{name:esc(x.name)})}">🗑</button>
    </div>`).join('');
  return `${head}<div class="bsec hidbox">
    <div class="bnote"><b>${base.count_before}</b> ${tt('buildings.on_the_line',{x:esc(base.ceiling_note||'')})}</div>
    <div class="brow" style="margin:6px 0">
      <input id="bldHidAdd" placeholder="new_resource_name" value="${esc(h.add||'')}"
        oninput="state.bld.hid.add=this.value" style="flex:0 0 220px">
      <button onclick="bldHidAsk('add',document.getElementById('bldHidAdd').value)">${tt('buildings.add_to_the_line')}</button>
      <span class="count">${tt('buildings.then_give_it_to_provinces_in')}</span>
    </div>
    ${h.pend?bldHidPendHtml(h):''}
    <div class="hidlist">${rows}</div></div>`;
}
function bldHidPendHtml(h){
  const p=h.plan;
  if(!p)return `<div class="bnote">${tt('buildings.working_out_what_that_touches')}</div>`;
  const rem=(p.impact||{}).removals||[];
  const dark=rem.filter(x=>x.clauses.length||x.provinces.length);
  const list=dark.map(x=>`<div class="hidimpact">
      <div><b>${esc(x.name)}</b>${tt('buildings.province_s_carry_it_clause_s',{provinces_n:x.provinces.length,clauses_n:x.clauses.length})}</div>
      ${x.provinces.length?`<div class="count">${tt('buildings.provinces',{x:x.provinces.map(v=>esc(v.settlement+' ('+v.region+')')).join(', ')})}</div>`:''}
      ${x.clauses.length?`<div class="hidclauses">${x.clauses.slice(0,200).map(c=>`<div><code>line ${c.line}</code> ${
        esc([c.building,c.level].filter(Boolean).join(' / '))} <span class="count">${esc(c.text)}</span></div>`).join('')}${
        x.clauses.length>200?`<div class="count">${tt('buildings.more_3',{clauses:x.clauses.length-200})}</div>`:''}</div>`:''}
    </div>`).join('');
  const errs=(p.errors||[]).filter(e=>!/acknowledge that first/.test(e));
  return `<div class="hidpend">
    <div><b>${p.changes.map(esc).join(', ')}</b> · ${p.impact.count_before} → ${p.impact.count_after}</div>
    ${errs.length?`<div class="w-bad">${errs.map(esc).join('<br>')}</div>`:''}
    ${list}
    ${dark.length?`<label class="chk w-warn"><input type="checkbox" ${h.ack?'checked':''}
        onchange="state.bld.hid.ack=this.checked;bldHidPaint()"> ${tt('buildings.i_understand_that_every_province_and')}</label>`:''}
    <div class="brow" style="margin-top:6px">
      <button class="primary" ${errs.length||(dark.length&&!h.ack)?'disabled':''} onclick="bldHidApply()">${tt('buildings.save_the_line')}</button>
      <button onclick="state.bld.hid.pend=null;state.bld.hid.plan=null;bldHidPaint()">${tt('common.cancel')}</button>
      <span class="count">${tt('buildings.backed_up_first_log_undoes_it')}</span>
    </div></div>`;
}
async function bldHidAsk(kind,name){
  const b=state.bld,h=b.hid;
  name=String(name||'').trim(); if(!name)return;
  h.pend={[kind]:[name]}; h.plan=null; h.ack=false;
  bldHidPaint();
  let r;
  try{ r=await api.post('/api/buildings/hidden/plan',Object.assign({mod:b.mod},h.pend)); }
  catch(e){ r={error:errText(e)}; }
  if(state.bld!==b)return;
  h.plan=r.plan||{changes:[],errors:[r.error||'failed'],impact:{removals:[]}};
  bldHidPaint();
}
async function bldHidApply(){
  const b=state.bld,h=b.hid;
  const body=Object.assign({mod:b.mod,clear_strings_bin:false},h.pend);
  if(h.ack)body.acknowledged=(h.pend.remove||[]);
  let r;
  try{ r=await api.post('/api/buildings/hidden/apply',body); }
  catch(e){ r={error:errText(e)}; }
  if(r.error){ toast(r.error,6000); return; }
  toast(tt('buildings.saved_undo_is_in_log',{x:(r.plan.changes||[]).join(', ')}),4200);
  b.ov=await api.get('/api/buildings?mod='+enc(b.mod));
  b.hidOpen=true;
  await bldHidLoad();
  render();
}

/* Edits staged against other building lines are invisible in this form - they
   belong to buildings that are not on screen - so they get a panel of their own.
   Without it, Save would write changes the page never showed. */
function bldAlsoHtml(){
  const also=(state.bld.work||{}).also||{};
  const lines=Object.keys(also).filter(l=>
    Object.values(also[l]).some(rows=>rows.length));
  if(!lines.length)return '';
  return `<div class="bsec ${foldCls('bld.also')}" data-fold="bld.also"><h4>${tt('buildings.also_changing_in_other_building_line',{bldAlsoCount:bldAlsoCount(),lines_n:lines.length})}
      <button style="margin-left:auto" onclick="bldAlsoClear()">${tt('buildings.drop_these')}</button></h4>
    ${lines.map(l=>`<div class="ckgroup"><div class="ckhead"><code>${esc(l)}</code></div>
      <div class="cklist">${Object.entries(also[l]).filter(([,r])=>r.length).map(([lvl,rows])=>`
        <div class="ckrow"><div class="ckwho"><div class="un">${esc(lvl)}</div>
          <div class="ut">${rows.map(r=>`${esc(r.pool.unit)} <span class="count">${
            r.line==null?'new':'edited'}</span>`).join(' · ')}</div></div>
          <button onclick="bldAlsoDrop('${q1(esc(l))}','${q1(esc(lvl))}')">${tt('buildings.drop')}</button></div>`
        ).join('')}</div></div>`).join('')}
    <div class="bnote">${tt('buildings.these_are_written_in_the_same')}</div></div>`;
}
function bldAlsoDrop(line,level){
  const also=(state.bld.work||{}).also||{};
  if(also[line])delete also[line][level];
  if(also[line]&&!Object.keys(also[line]).length)delete also[line];
  bldTouched(); renderBuildingEditor();
}
function bldAlsoClear(){
  state.bld.work.also={};
  bldTouched(); renderBuildingEditor();
}
function bldChecksInner(){
  const b=state.bld,ck=b.checks;
  if(!ck)return `<h4>${tt('buildings.checks')}</h4><div class="bnote">${tt('buildings.looking_over_the_whole_line')}</div>`;
  if(ck.error)return `<h4>${tt('buildings.checks')}</h4><div class="bnote w-bad">${esc(ck.error)}</div>`;
  const lvl=b.lvl, lv=b.work.levels[lvl];
  const gaps=(ck.gaps||[]).filter(g=>g.missing.includes(lvl)||g.first===lvl);
  const mir=(ck.mirror||[]).find(m=>m.level_index===lvl);
  const dupes=(ck.dupes||[]).filter(d=>d.level_index===lvl);
  const total=(ck.gaps||[]).length+(ck.dupes||[]).length+(ck.mirror||[]).length;
  if(!total)return `<h4>${tt('buildings.checks_clean')}</h4>
    <div class="bnote">${tt('buildings.every_unit_this_line_trains_is',{x:ck.twin?`${tt('buildings.and_it_matches')} <code>${esc(ck.twin)}</code>`:''})}</div>`;
  const rows=[];

  if(gaps.length)rows.push(`<div class="ckgroup"><div class="ckhead">
      <b class="w-warn">${gaps.length}</b> ${tt('buildings.unit_s_stop_being_recruitable_further')}
      <button onclick="bldFillGaps()">${tt('buildings.fill_every_gap')}</button></div>
    <div class="cklist">${gaps.map(g=>`<div class="ckrow">
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,g.pool.unit)}" alt="">
      <div class="ckwho"><div class="un">${esc(g.unit)}</div>
        <div class="ut">${tt('buildings.trained_at_missing_from',{x:g.present.map(bldLevelLabel).map(esc).join(', '),x2:g.missing_levels.map((n,i)=>esc(bldLevelLabel(g.missing[i]))).join(', ')})}</div></div>
      <button onclick="bldFillGap('${q1(esc(g.unit))}')">${tt('buildings.add_to_the_missing_tier_s')}</button>
    </div>`).join('')}</div></div>`);

  if(mir)rows.push(`<div class="ckgroup"><div class="ckhead">
      ${tt('buildings.this_tier_differs_from_only_here',{twin:esc(ck.twin),twin2:esc(mir.twin),only_here_n:mir.only_here.length,only_there_n:mir.only_there.length})}</div>
    <div class="cklist">
      ${mir.only_here.map(p=>bldMirrorRow(p,'push')).join('')}
      ${mir.only_there.map(p=>bldMirrorRow(p,'pull')).join('')}
    </div>
    <div class="brow" style="margin-top:6px">
      <button onclick="bldMirrorAll('push')">${tt('buildings.copy_all_into',{only_here_n:mir.only_here.length,twin:esc(ck.twin)})}</button>
      <button onclick="bldMirrorAll('pull')">${tt('buildings.bring_all_over_here',{only_there_n:mir.only_there.length})}</button>
    </div></div>`);

  if(dupes.length)rows.push(`<div class="ckgroup"><div class="ckhead">
      <b class="w-warn">${dupes.length}</b> ${tt('buildings.unit_s_listed_more_than_once')}</div>
    <div class="cklist">${dupes.map(d=>`<div class="ckrow">
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,d.unit)}" alt="">
      <div class="ckwho"><div class="un">${esc(d.unit)} <span class="badge">×${d.count}</span></div>
        <div class="ut">${d.same_requires
          ? `<span class="w-warn">${tt('buildings.every_copy_has_the_same_requirements')}</span>`
          : tt('buildings.the_copies_have_different_requirements_so')}</div></div>
      <button onclick="bldJumpPool('${q1(esc(d.unit))}')">${tt('buildings.show_the_rows')}</button>
    </div>`).join('')}</div></div>`);

  const elsewhere=total-(gaps.length+dupes.length+(mir?1:0));
  return `<h4>${tt('buildings.checks_across_the_whole_line',{total})}
      <button style="margin-left:auto" onclick="bldLoadChecks(true)">${tt('buildings.re_check')}</button></h4>
    ${rows.join('')||`<div class="bnote">${tt('buildings.nothing_to_flag_on_this_tier')}</div>`}
    ${elsewhere>0?`<div class="bnote">${tt('buildings.more_finding_s_on_other_tiers',{elsewhere})}</div>`:''}`;
}
// Scroll the recruitment list to a unit and flash its rows - the useful answer
// to "this unit is listed twice" is being shown both of them.
function bldJumpPool(unit){
  const key=unit.toLowerCase();
  const idx=bldCapList().map((c,i)=>[c,i])
    .filter(([c])=>c.pool&&c.pool.unit.toLowerCase()===key).map(([,i])=>i);
  if(!idx.length)return toast(tt('buildings.those_rows_are_hidden_by_the'));
  if(!foldIsOpen('bld.recruit'))foldSet('bld.recruit',true);
  const host=document.getElementById('bldPools'); if(!host)return;
  let first=null;
  idx.forEach(i=>{
    const el=host.querySelector(`[data-cap="${i}"]`); if(!el)return;
    first=first||el;
    el.classList.add('flash');
    setTimeout(()=>el.classList.remove('flash'),1600);
  });
  if(first)first.scrollIntoView({block:'center'});
  else toast(tt('buildings.those_rows_are_hidden_by_the'));
}
function bldMirrorRow(p,dir){
  return `<div class="ckrow">
    <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,p.unit)}" alt="">
    <div class="ckwho"><div class="un">${esc(p.unit)}</div>
      <div class="ut">${dir==='push'?tt('buildings.only_in_this_settlement_type'):tt('buildings.only_in_the_twin')}
        · ${POOL_LABEL.initial} ${esc(p.initial)}, ${POOL_LABEL.per_turn} ${esc(p.per_turn)},
        ${POOL_LABEL.maximum} ${esc(p.maximum)}, ${POOL_SHORT.experience} ${esc(p.experience)}</div></div>
    <button onclick="bldMirrorOne('${q1(esc(p.unit))}','${dir}')">${
      dir==='push'?tt('buildings.copy_to_the_twin'):tt('buildings.add_here')}</button></div>`;
}

/* ---- staging a pool into ANOTHER building line ----
   Rows go into work.also keyed by line then level. `line:null` marks a brand-new
   capability, exactly as a row added by hand in this editor does, so the server
   plans it through the same path. */
function bldAlso(line,level){
  const also=state.bld.work.also||(state.bld.work.also={});
  const byLevel=also[line]||(also[line]={});
  return byLevel[level]||(byLevel[level]=[]);
}
function bldAlsoCount(){
  const also=(state.bld.work||{}).also||{};
  return Object.values(also).reduce((n,byLevel)=>
    n+Object.values(byLevel).reduce((m,rows)=>m+rows.length,0),0);
}
function bldAlsoLines(){ return Object.keys((state.bld.work||{}).also||{}); }
// Whether the twin building already trains a unit at one of its levels - a
// mirror that duplicates what is there is exactly the "same unit twice" mistake
// the checks panel above flags.
function bldTwinHas(level,unit){
  const t=((state.bld.checks||{}).twin_units||{})[level]||[];
  return t.includes(unit.toLowerCase());
}
function bldStagePool(line,level,pool,conds){
  if(line===bldTwin()&&bldTwinHas(level,pool.unit))return false;
  const rows=bldAlso(line,level);
  if(rows.some(r=>r.pool.unit.toLowerCase()===pool.unit.toLowerCase()))return false;
  rows.push({line:null,keyword:'recruit_pool',args:'',
    requires:conds?bldClauseText(conds):(pool.requires||''),
    conds:conds||[],condEdited:!!conds,bonus:false,value:'',
    pool:{unit:pool.unit,initial:pool.initial,per_turn:pool.per_turn,
          maximum:pool.maximum,experience:pool.experience},
    comment:'',faction:false,del:false});
  return true;
}
// A pool already in THIS line's working copy, by unit and level. Used to avoid
// adding a second copy of something the level already trains.
function bldHasUnit(lvIndex,unit){
  const lv=state.bld.work.levels[lvIndex]; if(!lv)return false;
  const key=unit.toLowerCase();
  return [...lv.caps,...lv.fcaps].some(c=>c.pool&&!c.del&&c.pool.unit.toLowerCase()===key);
}

// "the tiers above" is only meaningful if it says WHICH - a barracks line can
// be five levels deep and the names are what the modder knows them by.
function bldTiersAboveNames(){
  const b=state.bld;
  return (b.d.levels||[]).slice(b.lvl+1).map((l,i)=>bldLevelLabel(b.lvl+1+i)).join(', ');
}
/* ---- fill the tiers above ---- */
// The numbers a mod gives a unit climb with the building, so a propagated copy
// climbs too rather than repeating tier 1's figures all the way up.
const BLD_TIER_BUMP={initial:0,per_turn:0,maximum:1,experience:0};
function bldBumped(pool,steps,bump){
  const num=(v,d)=>{const n=parseFloat(v);return isFinite(n)?n:d;};
  const b=bump||BLD_TIER_BUMP;
  return {unit:pool.unit,
    initial:numFmt(Math.max(0,num(pool.initial,1)+steps*num(b.initial,0))),
    per_turn:numFmt(Math.max(0,num(pool.per_turn,0.5)+steps*num(b.per_turn,0))),
    maximum:numFmt(Math.max(0,num(pool.maximum,2)+steps*num(b.maximum,0))),
    experience:numFmt(Math.max(0,Math.min(9,num(pool.experience,0)+steps*num(b.experience,0)))),
    requires:pool.requires};
}
function bldFillGap(unit){
  const b=state.bld,ck=b.checks||{};
  const g=(ck.gaps||[]).find(x=>x.unit===unit); if(!g)return;
  const n=bldFillGapRows(g);
  bldTouched(); renderBuildingEditor();
  toast(n?tt('buildings.added_to_tier_s',{unit,x:n}):tt('buildings.is_already_on_every_tier',{unit}));
}
function bldFillGaps(){
  const b=state.bld,ck=b.checks||{};
  let n=0;
  (ck.gaps||[]).forEach(g=>{n+=bldFillGapRows(g);});
  bldTouched(); renderBuildingEditor();
  toast(n?tt('buildings.pool_s_added_so_nothing_drops',{x:n})
         :tt('buildings.nothing_to_fill'));
}
function bldFillGapRows(g){
  const b=state.bld;
  let n=0;
  for(const i of g.missing){
    if(i>=b.work.levels.length||bldHasUnit(i,g.unit))continue;
    bldAddPoolRow(g.unit,i,bldBumped(g.pool,i-g.pool.level_index),null);
    n++;
  }
  return n;
}

/* ---- mirror into the city/castle twin ---- */
function bldMirrorOne(unit,dir){
  const b=state.bld,ck=b.checks||{};
  const m=(ck.mirror||[]).find(x=>x.level_index===b.lvl); if(!m)return;
  const list=dir==='push'?m.only_here:m.only_there;
  const p=list.find(x=>x.unit===unit); if(!p)return;
  if(!bldMirrorApply(p,dir,m))return toast(tt('buildings.is_already_there',{unit}));
  bldTouched(); renderBuildingEditor();
  toast(dir==='push'
    ? tt('buildings.staged_into_it_is_saved_with',{unit,twin:ck.twin,twin2:m.twin})
    : tt('buildings.added_to_this_tier',{unit}));
}
function bldMirrorAll(dir){
  const b=state.bld,ck=b.checks||{};
  const m=(ck.mirror||[]).find(x=>x.level_index===b.lvl); if(!m)return;
  const list=dir==='push'?m.only_here:m.only_there;
  let n=0; list.forEach(p=>{ if(bldMirrorApply(p,dir,m))n++; });
  if(!n)return toast(tt('buildings.nothing_left_to_copy'));
  bldTouched(); renderBuildingEditor();
  toast(dir==='push'?tt('buildings.unit_s_staged_into',{x:n,twin:ck.twin}):tt('buildings.unit_s_added_to_this_tier',{x:n}));
}
function bldMirrorApply(p,dir,m){
  const b=state.bld,ck=b.checks||{};
  if(dir==='push')return bldStagePool(ck.twin,m.twin,p,null);
  if(bldHasUnit(b.lvl,p.unit))return false;
  bldAddPoolRow(p.unit,b.lvl,p,null);
  return true;
}
// The ⇄ button on a pool row: put THIS row into the twin building at the tier
// that faces the one on screen.
function bldMirrorRowNow(i){
  const b=state.bld,c=bldCapList()[i]; if(!c||!c.pool)return;
  const twin=bldTwin(),level=bldTwinLevel();
  if(!twin||!level)return toast(tt('buildings.this_line_has_no_city_castle'));
  const ok=bldStagePool(twin,level,Object.assign({},c.pool,{requires:c.requires}),
                        c.condEdited?c.conds:null);
  if(!ok)return toast(bldTwinHas(level,c.pool.unit)
    ? tt('buildings.already_trains',{twin,level,unit:c.pool.unit})
    : tt('buildings.is_already_staged_for',{unit:c.pool.unit,twin}));
  bldTouched(); renderBuildingEditor();
  toast(tt('buildings.staged_into_it_is_saved_with_2',{unit:c.pool.unit,twin,level}),4000);
}
// …and the same row pushed up every tier above this one.
function bldTiersRowNow(i){
  const b=state.bld,c=bldCapList()[i]; if(!c||!c.pool)return;
  let n=0;
  for(let j=b.lvl+1;j<b.work.levels.length;j++){
    if(bldHasUnit(j,c.pool.unit))continue;
    bldAddPoolRow(c.pool.unit,j,bldBumped(Object.assign({},c.pool,{requires:c.requires}),j-b.lvl),
                  c.condEdited?c.conds:null);
    n++;
  }
  if(!n)return toast(tt('buildings.is_already_trained_at_every_tier',{unit:c.pool.unit}));
  bldTouched(); renderBuildingEditor();
  toast(tt('buildings.added_to_higher_tier_s',{unit:c.pool.unit,x:n}));
}

/* =========================================================================
   The city half and the castle half, side by side

   A settlement building is written as TWO lines in the EDB with nothing tying
   them together - `barracks` and `castle_barracks` are as unrelated to the file
   as any two buildings in it - so over years of edits they drift. A unit gets
   added to the city chain and forgotten in the castle one, and the only way to
   find that was to open both lines and read them against each other by eye.

   This panel is that reading, done for you. Tier by tier, every unit either half
   trains, and what each half gives it. `⇄ Mirror` closes one gap; `⇄ Mirror all`
   closes every gap on the tier or in the whole line.

   Nothing here writes to disk. A unit copied INTO this line goes into its
   working copy exactly as one added by hand does; a unit copied into the twin is
   staged in `work.also` and appears in the editor's "Also changing" panel. Both
   are written by the same Save, with the same backup and the same Undo - the
   same road every other edit in this editor takes.
   ========================================================================= */
async function bldCompareVariants(){
  const b=state.bld; if(!b||!b.line)return;
  const modal=document.getElementById('modal');
  if(!b.stash){b.stashScroll=stashPlace(); b.stash=modal.innerHTML;}
  modal.innerHTML=`<h2>${tt('buildings.city_and_castle_side_by_side')}</h2>
    <div class="mbody"><div class="empty">${tt('buildings.reading_both_halves_of_this_building')}</div></div>
    <div class="foot"><button onclick="bldPickCancel()">${tt('buildings.back')}</button></div>`;
  let r;
  try{ r=await api.get(`/api/buildings/variants?mod=${enc(b.mod)}&line=${enc(b.line)}`
                       +`&culture=${enc(b.culture||'')}`); }
  catch(e){ r={error:''+e}; }
  if(!r||r.error){
    modal.querySelector('.mbody').innerHTML=`<div class="w-bad">${esc((r&&r.error)||tt('buildings.no_answer'))}</div>`;
    return;
  }
  activity(tt('buildings.compared_city_castle'),tt('buildings.against_in',{line:b.line,twin:r.twin||'nothing',mod:b.mod}));
  b.vc={r,only:'gaps'};
  bldVarRender();
}
// Which rows the panel shows. Both halves of a real building agree about most of
// their roster, so "everything" is a thousand rows of nothing to do - the gaps
// are what the panel is opened for, and they lead.
function bldVarFilter(v){ if(state.bld.vc){state.bld.vc.only=v; bldVarRender();} }
function bldVarRows(lv){
  const only=(state.bld.vc||{}).only;
  if(only==='all')return lv.units;
  if(only==='numbers')return lv.units.filter(u=>u.where!=='both'||u.numbers_differ);
  return lv.units.filter(u=>u.where!=='both');
}
// Which side of the panel is which settlement type, in the reader's words.
const bldVarSide=(r,side)=>side==='a'
  ? (r.settlement||tt('buildings.this_half')) : (r.twin_settlement||tt('buildings.the_other_half'));
function bldVarRender(){
  const b=state.bld,vc=b.vc; if(!vc)return;
  const r=vc.r;
  const modal=document.getElementById('modal');
  if(!r.twin){
    modal.innerHTML=`<h2>${tt('buildings.city_and_castle_side_by_side')}</h2>
      <div class="mbody"><div class="bnote">${esc(r.reason||'')}${docPoints('',[
        tt('buildings.pair_matched_by_name'),
        tt('buildings.line_in_both_has_no_second_half')])}</div></div>
      <div class="foot"><button onclick="bldPickCancel()">${tt('buildings.back')}</button></div>`;
    return;
  }
  const gaps=r.only_a+r.only_b;
  const tab=(k,label,n)=>`<button class="${vc.only===k?'on':''}"
    onclick="bldVarFilter('${k}')">${label}${n==null?''
      :` <span class="badge" id="vcTab_${k}">${n}</span>`}</button>`;
  modal.innerHTML=`<h2>${tt('buildings.city_and_castle_side_by_side_2',{x:esc(r.line_label||r.line)})}</h2>
    <div class="mbody">
      <div class="vchead">
        <div class="vcside"><span class="badge">${esc(r.settlement)}</span>
          <b>${esc(r.line_label||r.line)}</b><code>${esc(r.line)}</code></div>
        <div class="vcvs">⇄</div>
        <div class="vcside"><span class="badge cls">${esc(r.twin_settlement)}</span>
          <b>${esc(r.twin_label||r.twin)}</b><code>${esc(r.twin)}</code></div>
      </div>
      <div class="count">${docPoints(gaps
        ? tt('buildings.gaps_trained_by_one_half',{gaps})
        : tt('buildings.both_halves_train_the_same_units'),[
        r.differs?tt('buildings.differs_trained_by_both',{differs:r.differs}):'',
        tt('buildings.differing_clause_not_counted'),
        tt('buildings.four_numbers_can_be_typed_into'),
        tt('buildings.nothing_written_until_save')])}</div>
      <div class="sndtabs" style="margin:8px 0">
        ${tab('gaps',tt('buildings.only_on_one_side'),gaps)}
        ${tab('numbers',tt('buildings.gaps_and_different_numbers'),gaps+r.differs)}
        ${tab('all',tt('buildings.every_unit'),r.levels.reduce((n,l)=>n+l.units.length,0))}
        ${gaps?`<button class="primary" style="margin-left:auto"
          onclick="bldVarMirrorAll()">${tt('buildings.mirror_every_gap',{gaps})}</button>`:''}
      </div>
      ${r.levels.map(bldVarLevelHtml).join('')}
    </div>
    <div class="foot">
      <span class="count">${bldAlsoCount()?tt('buildings.row_s_staged_for_other_lines',{bldAlsoCount:bldAlsoCount()}):''}</span>
      <button onclick="bldPickCancel()">${tt('buildings.back_to_the_building')}</button>
    </div>`;
  bldVarWire();
}
/* The boxes are live from the keystroke, not from an Apply button: this panel
   has never had one - a mirror is staged the moment it is clicked - and a second
   way of saying "yes, that number" would only be a way of losing one. */
function bldVarWire(){
  const modal=document.getElementById('modal');
  wireNumBoxes(modal);
  modal.querySelectorAll('[data-vc]').forEach(inp=>{
    inp.addEventListener('input',()=>bldVarSet(+inp.dataset.vcli,inp.dataset.vcu,
                                               inp.dataset.vcside,inp.dataset.vc,inp.value));
  });
}
function bldVarLevelHtml(lv,i){
  const r=state.bld.vc.r;
  const rows=bldVarRows(lv);
  const gaps=lv.only_a+lv.only_b;
  if(!lv.twin_level)
    return `<fieldset class="vclv"><legend>${esc(lv.level_label||lv.level)}</legend>
      <div class="bnote">${tt('buildings.this_tier_has_no_facing_tier',{twin:esc(r.twin)})}</div></fieldset>`;
  // The column names go on the line directly above the boxes, which is the only
  // place they fit: a box is 66px wide, and the long name and what the number
  // does are on the box's own tooltip.
  const head=side=>`<span class="vcn"><b>${esc(side)}</b>
    <span class="vcnums">${VAR_NUM_KEYS.map(k=>`<span title="${esc(POOL_LABEL[k])}">${
      esc(VAR_NUM_HEAD[k])}</span>`).join('')}</span></span>`;
  return `<fieldset class="vclv"><legend>${tt('buildings.tier',{x:esc(lv.level_label||lv.level),x2:i+1,x3:esc(lv.twin_level_label||lv.twin_level)})}</legend>
    <div class="vcbar">
      <span class="count" id="vcBar_${i}">${bldVarBarText(lv)}</span>
      ${gaps?`<button style="margin-left:auto" onclick="bldVarMirrorLevel(${i})"
        title="${ttA('buildings.copy_every_unit_this_tier_is')}">
        ${tt('buildings.mirror_this_tier',{gaps})}</button>`:''}
    </div>
    ${rows.length?`<div class="vclist">
      <div class="vcrow vchd">${tt('buildings.unit_trained_by',{x:head(r.settlement),x2:head(r.twin_settlement)})}</div>
      ${rows.map(u=>bldVarRowHtml(u,i)).join('')}</div>`
     :`<div class="bnote">${tt('buildings.nothing_to_show_here_with_the')}</div>`}
  </fieldset>`;
}
// The tier's one-line tally. Its own function because a number typed into a box
// can change it, and repainting the line is cheaper - and far less rude - than
// redrawing the panel out from under the caret.
function bldVarBarText(lv){
  const gaps=lv.only_a+lv.only_b;
  return tt('buildings.unit_s_across_both_halves',{units_n:lv.units.length,gaps:gaps?` ${tt('buildings.on_one_side_only',{gaps})}`:tt('buildings.none_missing'),x:lv.differs?tt('buildings.with_different_numbers',{differs:lv.differs}):''});
}
//: The four numbers of a pool, in the order the `recruit_pool` line writes them.
const VAR_NUM_KEYS=['initial','per_turn','maximum','experience'];
//: How far one ▲▼ click moves each of them - a rate steps by a whole TURN, and a
//: pool count steps through 0.99 (see numBump).
const VAR_NUM_STEP={initial:'pool',per_turn:'turns',maximum:'pool',experience:'1'};
//: Short enough to sit over a box, and to name a difference in the row's own
//: column. POOL_LABEL has the full name.
const VAR_NUM_HEAD={initial:tt('buildings.initial'),per_turn:tt('buildings.rate'),maximum:tt('buildings.max'),experience:'XP'};
/* The four numbers of one side, editable wherever that side trains the unit.

   Read-only, this panel could say that the two halves disagree and nothing more:
   the fix was two further trips into two separate building forms, one of them
   for a line that is not even the one you have open. A number typed here is
   staged the moment it is typed, exactly as the ⇄ Mirror beside it is - into the
   working copy for this half, into `also` for the twin. Nothing reaches disk
   until the building is saved, and one Undo takes the lot back.

   A side that does not train the unit has no numbers to show and none to take:
   that is a gap, and ⇄ Mirror is what closes it. */
function bldVarNums(u,li,side){
  const p=side==='a'?u.a:u.b;
  if(!p)return `<span class="vcnums"><span class="w-warn">${tt('buildings.not_trained')}</span></span>`;
  return `<span class="vcnums">${VAR_NUM_KEYS.map(k=>numBox(
    `data-vc="${k}" data-vcside="${side}" data-vcli="${li}" data-vcu="${esc(u.unit)}" title="${esc(POOL_LABEL[k])}"`,
    p[k],VAR_NUM_STEP[k])).join('')}</span>`;
}
// All four across the divide at once, which is the commonest thing to want once
// the two halves are side by side and one of them is plainly the right one.
function bldVarCopyBtn(u,li,from){
  if(u.where!=='both')return '';
  const r=state.bld.vc.r;
  const src=from==='a'?r.settlement:r.twin_settlement;
  const dst=from==='a'?r.twin_settlement:r.settlement;
  return `<button class="vccopy" onclick="bldVarCopy(${li},'${q1(esc(u.unit))}','${from}')"
    title="${ttA('buildings.put_all_four_of_the_halfs',{src:esc(src),dst:esc(dst)})}"
    >${tt('buildings.copy',{src:esc(src),dst:esc(dst)})}</button>`;
}
function bldVarRowHtml(u,li){
  const r=state.bld.vc.r;
  const where=u.where==='both'
    ? `<span class="badge good" title="${ttA('buildings.both_halves_of_this_building_train')}">${tt('buildings.both')}</span>`
    : u.where==='a'
      ? `<span class="badge" title="${ttA('buildings.only_the_half_trains_it_here',{settlement:esc(r.settlement)})}">${tt('buildings.only',{settlement:esc(r.settlement)})}</span>`
      : `<span class="badge cls" title="${ttA('buildings.only_the_half_trains_it_here_2',{twin_settlement:esc(r.twin_settlement)})}">${tt('buildings.only_2',{twin_settlement:esc(r.twin_settlement)})}</span>`;
  return `<div class="vcrow ${u.where==='both'?'':'gap'}" data-vcrow="${esc(bldVarKey(li,u.unit))}">
    <span class="vcu">
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,u.unit)}" alt="">
      <span class="vcnm"><span class="nm">${esc(u.name||u.unit)}</span>
        <span class="ty">${u.missing?`<span class="w-bad">${tt('buildings.not_in_this_mods_edu')}</span>`
                                     :esc(u.unit)}</span></span></span>
    <span class="vcw">${where}</span>
    <span class="vcn ${u.where==='b'?'off':''}">${bldVarNums(u,li,'a')}${bldVarCopyBtn(u,li,'a')}</span>
    <span class="vcn ${u.where==='a'?'off':''}">${bldVarNums(u,li,'b')}${bldVarCopyBtn(u,li,'b')}</span>
    <span class="vca">${bldVarActHtml(u,li)}</span></div>`;
}
// What the row's last column says: which of the four disagree, or the offer to
// close a gap. Repainted on its own when a box is typed into.
function bldVarActHtml(u,li){
  if(u.where!=='both')
    return `<button onclick="bldVarMirrorOne(${li},'${q1(esc(u.unit))}')"
      title="${ttA('buildings.copy_this_unit_into_the_half')}"
      >${tt('buildings.mirror')}</button>`;
  if(!u.numbers_differ)return `<span class="count">${tt('buildings.in_step')}</span>`;
  return `<span class="count" title="${esc((u.diff||[]).join(', '))}">${tt('buildings.different',{x:esc((u.diff||[]).filter(f=>f!=='requires').map(f=>VAR_NUM_HEAD[f]||f).join(', '))})}</span>`;
}
//: Which row on screen a unit is, for the repaints below. Tier index and unit
//: name: a unit appears once per tier, and the panel keys everything by name.
const bldVarKey=(li,unit)=>li+'|'+unit;

/* ---- a number typed into one of the boxes ----

   Which side it was typed on decides where it is staged, and both answers are
   ones this editor already had:

   * this half is the line the form behind the panel has open, so its row is
     already in the working copy - found by the EDB line it came from, the same
     key the unit view uses, falling back to the unit name for a row this panel
     staged a moment ago (a mirrored row has no line in the file yet);
   * the twin is a building that is not on screen, so its row is staged in
     `work.also` against the line it occupies. That is an in-place rewrite rather
     than a second copy of the unit, and it appears under "Also changing" like
     every other edit made to a building from somewhere else.

   The panel's own copy of the answer is edited too, so the marks beside the box
   stay honest without a redraw that would take the box out from under the caret. */
function bldVarSet(li,unit,side,key,val){
  const vc=state.bld.vc; if(!vc)return;
  const lv=vc.r.levels[li]; if(!lv)return;
  const u=lv.units.find(x=>x.unit===unit); if(!u)return;
  const p=side==='a'?u.a:u.b; if(!p)return;
  p[key]=val;
  if(side==='a')bldVarStageHere(lv,u); else bldVarStageTwin(lv,u);
  bldVarRepaint(li,lv,u);
  bldTouched();
}
const bldVarPool=p=>({unit:p.unit,initial:p.initial,per_turn:p.per_turn,
                      maximum:p.maximum,experience:p.experience});
function bldVarStageHere(lv,u){
  const work=state.bld.work.levels[lv.level_index]; if(!work||!u.a)return;
  const rows=[...work.caps,...work.fcaps].filter(c=>c.pool&&!c.del);
  const key=u.unit.toLowerCase();
  const row=(u.a.cap_line!=null&&rows.find(c=>c.line===u.a.cap_line))
         ||rows.find(c=>c.pool.unit.toLowerCase()===key);
  if(row)Object.assign(row.pool,bldVarPool(u.a));
}
function bldVarStageTwin(lv,u){
  const r=state.bld.vc.r;
  if(!lv.twin_level||!u.b)return;
  const rows=bldAlso(r.twin,lv.twin_level),key=u.unit.toLowerCase();
  const at=u.b.cap_line==null?null:u.b.cap_line;
  const prev=(at!=null&&rows.find(x=>x.pool&&x.line===at))
          ||rows.find(x=>x.pool&&x.pool.unit.toLowerCase()===key);
  if(prev){Object.assign(prev.pool,bldVarPool(u.b)); return;}
  // The clause goes back as the text the file already holds: re-emitting an
  // untouched one from structure would quietly re-tidy it, and a city clause and
  // a castle clause are supposed to differ.
  rows.push({line:at,keyword:'recruit_pool',args:'',requires:u.b.requires||'',
    conds:[],condEdited:false,bonus:false,value:'',pool:bldVarPool(u.b),
    comment:'',faction:!!u.b.faction,del:false});
}
// Which of the four now disagree, and the clause with them: the server works
// this out on the way in, and a typed number is the one thing that can change it
// afterwards.
function bldVarDiff(u){
  if(u.where!=='both'||!u.a||!u.b)return;
  const same=k=>String(u.a[k]).trim()===String(u.b[k]).trim();
  const diff=VAR_NUM_KEYS.filter(k=>!same(k));
  u.numbers_differ=diff.length>0;
  if(!same('requires'))diff.push('requires');
  u.diff=diff; u.same=!diff.length;
}
// The row's last column, the tier's tally and the tab that counts differences:
// everything a typed number makes stale, and nothing else. A row that has just
// come into step is NOT taken off a filtered list - pulling the line you are
// typing on out from under you would be the worst possible reward for fixing it.
function bldVarRepaint(li,lv,u){
  const r=state.bld.vc.r;
  bldVarDiff(u);
  lv.differs=lv.units.filter(x=>x.numbers_differ).length;
  r.differs=r.levels.reduce((n,l)=>n+l.differs,0);
  const modal=document.getElementById('modal');
  const cell=modal.querySelector(`.vcrow[data-vcrow="${cssq(bldVarKey(li,u.unit))}"] .vca`);
  if(cell)cell.innerHTML=bldVarActHtml(u,li);
  const bar=document.getElementById('vcBar_'+li);
  if(bar)bar.innerHTML=bldVarBarText(lv);
  const tab=document.getElementById('vcTab_numbers');
  if(tab)tab.textContent=r.only_a+r.only_b+r.differs;
}
/* ⇄ Copy: all four numbers from one half onto the other, in one click. */
function bldVarCopy(li,unit,from){
  const vc=state.bld.vc; if(!vc)return;
  const lv=vc.r.levels[li]; if(!lv)return;
  const u=lv.units.find(x=>x.unit===unit); if(!u||u.where!=='both')return;
  const r=vc.r;
  const src=from==='a'?u.a:u.b, dst=from==='a'?u.b:u.a;
  if(!src||!dst)return;
  const from_label=from==='a'?r.settlement:r.twin_settlement;
  const into=from==='a'?r.twin_settlement:r.settlement;
  if(VAR_NUM_KEYS.every(k=>String(src[k]).trim()===String(dst[k]).trim()))
    return toast(tt('buildings.the_half_already_trains_with_those',{into,x:u.name||u.unit}));
  VAR_NUM_KEYS.forEach(k=>{dst[k]=src[k];});
  if(from==='a')bldVarStageTwin(lv,u); else bldVarStageHere(lv,u);
  bldVarDiff(u);
  lv.differs=lv.units.filter(x=>x.numbers_differ).length;
  r.differs=r.levels.reduce((n,l)=>n+l.differs,0);
  bldTouched(); bldVarRender();
  toast(tt('buildings.halfs_numbers_put_onto_other_half',{name:u.name||u.unit,from_label,into}),4200);
}
/* Copy one unit into the half that does not train it.

   Into THIS line it is an ordinary added row in the working copy; into the twin
   it is an `also` row, staged against that line's own level. Both go through the
   calls the single-row ⇄ on a pool row already uses, so a mirror from here and a
   mirror from there stage identically. */
function bldVarMirrorApply(lv,u){
  const r=state.bld.vc.r;
  if(u.where==='a'){                          // this half has it, the twin does not
    return bldStagePool(r.twin,lv.twin_level,u.a,null);
  }
  if(bldHasUnit(lv.level_index,u.unit))return false;
  bldAddPoolRow(u.unit,lv.level_index,u.b,null);
  return true;
}
// The panel's own copy of the answer is what it draws from, so a mirrored row
// has to be marked there too or it would offer the same button again.
function bldVarTake(lv,u){
  // The copy is a row that does not exist in the file yet, so it carries no line
  // of its own and sits in an ordinary capability block. Letting it keep the
  // other side's `cap_line` would point a later edit of these boxes at a line in
  // the WRONG building.
  const fresh=p=>Object.assign({},p,{cap_line:null,faction:false});
  if(u.where==='a'){u.b=fresh(u.a);}
  else{u.a=fresh(u.b);}
  u.where='both'; u.same=true; u.diff=[]; u.numbers_differ=false; u.staged=true;
  lv.only_a=lv.units.filter(x=>x.where==='a').length;
  lv.only_b=lv.units.filter(x=>x.where==='b').length;
  const r=state.bld.vc.r;
  r.only_a=r.levels.reduce((n,l)=>n+l.only_a,0);
  r.only_b=r.levels.reduce((n,l)=>n+l.only_b,0);
}
function bldVarMirrorOne(li,unit){
  const vc=state.bld.vc; if(!vc)return;
  const lv=vc.r.levels[li]; if(!lv)return;
  const u=lv.units.find(x=>x.unit===unit); if(!u||u.where==='both')return;
  const into=u.where==='a'?vc.r.twin_settlement:vc.r.settlement;
  if(!bldVarMirrorApply(lv,u))return toast(tt('buildings.is_already_staged_there',{unit}));
  bldVarTake(lv,u);
  bldTouched(); bldVarRender();
  toast(tt('buildings.staged_into_the_half_save_the',{unit,into}),4000);
}
function bldVarMirrorLevel(li){
  const vc=state.bld.vc; if(!vc)return;
  const lv=vc.r.levels[li]; if(!lv)return;
  let n=0;
  lv.units.filter(u=>u.where!=='both').forEach(u=>{
    if(bldVarMirrorApply(lv,u)){bldVarTake(lv,u); n++;}
  });
  if(!n)return toast(tt('buildings.nothing_left_to_copy_on_this'));
  bldTouched(); bldVarRender();
  toast(tt('buildings.unit_s_staged_save_the_building',{x:n}),4000);
}
function bldVarMirrorAll(){
  const vc=state.bld.vc; if(!vc)return;
  let n=0;
  vc.r.levels.forEach(lv=>{
    if(!lv.twin_level)return;
    lv.units.filter(u=>u.where!=='both').forEach(u=>{
      if(bldVarMirrorApply(lv,u)){bldVarTake(lv,u); n++;}
    });
  });
  if(!n)return toast(tt('buildings.nothing_left_to_copy'));
  bldTouched(); bldVarRender();
  toast(tt('buildings.unit_s_staged_across_every_tier',{x:n}),5000);
}

/* ---- the same unit, everywhere it is recruited ----
   A unit is typically trained from four or five buildings whose numbers drifted
   apart over years of edits, and no view in the mod puts them side by side. This
   one does, and edits them in place: rows in the building on screen go into its
   working copy, rows in other lines are staged as `also` edits keyed by the EDB
   line they already occupy. */
async function bldShowUnit(unit){
  const b=state.bld;
  const modal=document.getElementById('modal');
  if(!b.stash){b.stashScroll=stashPlace();b.stash=modal.innerHTML;}
  modal.innerHTML=`<h2>${tt('buildings.everywhere_it_is_recruited',{unit:esc(unit)})}</h2>
    <div class="mbody"><div class="empty">${tt('buildings.reading_every_building_line')}</div></div>
    <div class="foot"><button onclick="bldPickCancel()">${tt('buildings.back')}</button></div>`;
  let r;
  try{ r=await api.get(`/api/buildings/unit?mod=${enc(b.mod)}&type=${enc(unit)}`
                       +`&culture=${enc(b.culture||'')}`); }
  catch(e){ r={error:''+e}; }
  if(r.error){ modal.querySelector('.mbody').innerHTML=`<div class="w-bad">${esc(r.error)}</div>`; return; }
  b.cmp={unit,r,edits:{}};
  bldUnitRender();
}
function bldUnitRows(){
  const c=state.bld.cmp; return c?c.r.instances:[];
}
// One number, as the panel currently has it (edited value wins).
function bldUnitVal(row,key){
  const e=state.bld.cmp.edits[row.cap_line];
  return (e&&e[key]!==undefined)?e[key]:row[key];
}
function bldUnitSet(cap,key,val){
  const e=state.bld.cmp.edits, cur=e[cap]||(e[cap]={});
  cur[key]=val;
  bldUnitPaintDirty();
}
function bldUnitDirtyRows(){
  const c=state.bld.cmp;
  return bldUnitRows().filter(r=>{
    const e=c.edits[r.cap_line]; if(!e)return false;
    if(e.condEdited)return true;
    return ['initial','per_turn','maximum','experience']
      .some(k=>e[k]!==undefined&&String(e[k]).trim()!==String(r[k]).trim());
  });
}
/* ---- the unit view's own Code View ----
   Read-only, because this screen is the one shape in the toolkit that is not a
   record: its rows come from a dozen building blocks scattered through the EDB,
   so there is nothing for a serialiser to write back to. What it answers is the
   question the boxes cannot - what do these pools actually SAY in the file -
   and hovering a row lights its line. See codeview.pools_document. */
function bldUnitCvHost(){
  const c=state.bld.cmp;
  return {kind:'pools', mod:state.bld.mod, id:c.unit, readonly:true,
          where:'data/export_descr_buildings.txt',
          rerender:()=>bldUnitRender()};
}
async function bldUnitCvToggle(){
  const b=state.bld,c=b.cmp;
  if(c.cv){cvDrop(c.cv); c.cv=null; bldUnitRender(); return;}
  c.cv=cvCreate(bldUnitCvHost());
  bldUnitRender();                       // draw the empty pane, then fill it
  await cvLoad(c.cv);
  if(state.bld.cmp===c)bldUnitRender();
}
// The requires clause as this panel currently has it (an edit wins over the file).
function bldUnitReq(row){
  const e=state.bld.cmp.edits[row.cap_line];
  return (e&&e.condEdited)?(e.requires||''):(row.requires||'');
}
/* Editing a requires clause from the UNIT side.
   The same dialog the building editor uses, given a host of our own: these rows
   come from building lines that are mostly not loaded into `b.work`, so there
   is no capability object to hand it. The edit is kept in `cmp.edits` beside
   the numbers and staged by the same Apply, which is what makes a requirement
   edited here save exactly like one edited from the building view. */
function bldUnitEditReq(i){
  const b=state.bld,r=bldUnitRows()[i]; if(!r)return;
  const e=b.cmp.edits[r.cap_line]||(b.cmp.edits[r.cap_line]={});
  const conds=e.condEdited?e.conds:(r.conditions||[]);
  b.clause={host:e,kind:'unit',index:i,unit:b.cmp.unit,units:[b.cmp.unit],pick:null,
            conds:JSON.parse(JSON.stringify(conds||[])),
            was:JSON.parse(JSON.stringify(conds||[]))};
  bldClauseStash();
  renderClauseDialog();
  bldClauseOwnership();
}
function bldUnitPaintDirty(){
  const n=bldUnitDirtyRows().length;
  const el=document.getElementById('bcCount');
  if(el)el.textContent=n?tt('buildings.row_s_changed',{x:n}):tt('buildings.nothing_changed_yet');
  const btn=document.getElementById('bcApply');
  if(btn){btn.disabled=!n;btn.textContent=n?tt('buildings.stage_change_s',{x:n}):tt('buildings.stage_changes');}
}
function bldUnitRender(){
  const b=state.bld,c=b.cmp,rows=bldUnitRows();
  //: The EDU/EDB keyword on the left, what the column is CALLED on the right.
  //: "start / per turn / max" said what the numbers were shaped like and not
  //: what they do; these are the names the same three fields now carry
  //: everywhere the toolkit shows them.
  const KEYS=[['initial',POOL_LABEL.initial],['per_turn',POOL_LABEL.per_turn],
              ['maximum',POOL_LABEL.maximum],['experience',POOL_SHORT.experience]];
  // A value that is not the one most of the rows use is what you came here to
  // find, so it is marked rather than left to be spotted.
  const common=KEYS.map(([k])=>{
    const tally={};
    rows.forEach(r=>{const v=String(bldUnitVal(r,k)).trim();tally[v]=(tally[v]||0)+1;});
    return Object.entries(tally).sort((x,y)=>y[1]-x[1])[0]||['',0];
  });
  document.getElementById('modal').innerHTML=`<h2>${tt('buildings.recruit_pool_s',{x:esc(c.r.info.name||c.unit),rows_n:esc(rows.length)})}</h2>
    <div class="mbody">
      <div class="ehead">
        <img style="width:60px;height:48px" onerror="iconRetry(this)" src="${iconUrl(state.src,c.unit)}">
        <div><div class="nm">${esc(c.r.info.name||c.unit)}</div>
          <div class="count"><code>${esc(c.unit)}</code>${c.r.info.missing
            ?` ${tt('buildings.not_in_this_mods_edu_3')}`:''}</div>
          <div class="count">${tt('buildings.every_building_line_that_trains_it')}</div></div>
      </div>
      <div class="cvsplit${c.cv?'':' off'}">
        <div id="bcGui">${rows.length?`<div class="poollist" id="bcList">
          <div class="bcrow bchead">${tt('buildings.building_tier_twin_requires',{KEYS:KEYS.map(([k,l])=>`<span class="bcn" title="${esc(POOL_HELP[k]||'')}">${esc(l)}</span>`).join('')})}</div>
          ${rows.map((r,i)=>bldUnitRow(r,i,KEYS,common)).join('')}
        </div>`:`<div class="bnote">${tt('buildings.no_building_line_trains_this_unit')}</div>`}</div>
        ${c.cv?`<div style="padding-top:4px">${cvHtml(c.cv)}</div>`:''}
      </div>
      <div class="bnote">${tt('buildings.a_tier_is_shown_as_its')}</div>
    </div>
    <div class="foot"><span class="count" id="bcCount"></span>
      <button class="${c.cv?'on':''}" title="${ttA('buildings.show_the_recruit_pool_lines_these')}"
        onclick="bldUnitCvToggle()">${tt('common.code_view')}</button>
      <button onclick="bldPickCancel()">${tt('buildings.back')}</button>
      <button class="primary" id="bcApply" onclick="bldUnitApply()">${tt('buildings.stage_changes')}</button></div>`;
  wireNumBoxes(document.getElementById('modal'));
  document.getElementById('modal').querySelectorAll('[data-bc]').forEach(inp=>{
    inp.addEventListener('input',()=>bldUnitSet(+inp.dataset.bcline,inp.dataset.bc,inp.value));
  });
  if(c.cv){cvWire(c.cv); cvBindHover(c.cv,document.getElementById('bcGui'));}
  bldUnitPaintDirty();
}
function bldUnitRow(r,i,KEYS,modal){
  const here=r.line===state.bld.line;
  const req=bldUnitReq(r), reqEdited=req!==(r.requires||'');
  return `<div class="bcrow ${here?'here':''}" data-label="pool:${r.cap_line}">
    <span class="bcb" title="${esc(r.line)}">${esc(r.line_label||r.line)}
      <span class="badge ${r.settlement==='castle'?'cls':''}">${esc(r.settlement||'both')}</span>
      ${here?`<span class="badge good" title="${ttA('buildings.this_is_the_building_line_you')}">${tt('buildings.open_3')}</span>`:''}</span>
    <span class="count" title="${esc(r.level)}">${esc(r.level_label||r.level)}
      <span class="count">(${r.level_index+1}/${r.level_count})</span></span>
    ${bldUnitTwinCell(r)}
    ${KEYS.map(([k],j)=>{
      const v=bldUnitVal(r,k);
      const odd=String(v).trim()!==modal[j][0];
      return `<span class="bcn ${odd?'odd':''}" title="${odd?ttA('buildings.differs_from_what_most_pools_use_value',{value:esc(modal[j][0])}):''}">
        ${numBox(`data-bc="${k}" data-bcline="${r.cap_line}"`,v,k==='per_turn'?'turns':(k==='experience'?'1':'pool'))}</span>`;
    }).join('')}
    <span class="count bcreq ${reqEdited?'changed':''}" title="${esc(req||tt('buildings.no_conditions'))}"><span>${
      esc(req||tt('common.none_2'))}</span>
      <button class="reqbtn" title="${ttA('buildings.edit_who_can_recruit_it_from')}"
        onclick="bldUnitEditReq(${i})">✎</button></span></div>`;
}
/* Does the settlement's other half train this unit at the facing tier?
   A city/castle pair drifting apart is what this panel is opened to find, and
   the answer is per TIER: a twin that trains the unit five levels up is not the
   same building. `⇄ Mirror` puts the row into the twin, staged like every other
   edit - the same call the building editor's own mirror uses. */
function bldUnitTwinCell(r){
  if(!r.twin)
    return `<span class="count bctw" title="${ttA('buildings.this_building_line_has_no_city')}">${tt('common.none_2')}</span>`;
  if(!r.twin_level)
    return `<span class="count bctw" title="${ttA('buildings.has_no_tier_facing_this_one',{twin:esc(r.twin)})}">${tt('buildings.no_tier')}</span>`;
  const where=`${r.twin} · ${r.twin_level_label||r.twin_level}`;
  if(r.twin_has)
    return `<span class="count bctw" title="${ttA('buildings.trains_it_too',{where:esc(where)})}"><span class="badge good">✓</span></span>`;
  return `<span class="count bctw"><span class="w-warn" title="${ttA('buildings.does_not_train_this_unit',{where:esc(where)})}">✗</span>
    <button class="reqbtn" title="${ttA('buildings.copy_this_pool_into_staged_with',{where:esc(where)})}"
      onclick="bldUnitMirror(${r.level_index},'${q1(esc(r.line))}')">⇄</button></span>`;
}
// ⇄ from the unit view: stage this pool into the twin building's facing tier.
// It goes through bldStagePool like every other mirror, so it lands in the same
// `also` bucket, refuses a duplicate the same way, and rides the same Save.
function bldUnitMirror(levelIndex,line){
  const b=state.bld,c=b.cmp;
  const r=bldUnitRows().find(x=>x.line===line&&x.level_index===levelIndex);
  if(!r||!r.twin_level)return;
  const pool={unit:c.unit,
    initial:bldUnitVal(r,'initial'),per_turn:bldUnitVal(r,'per_turn'),
    maximum:bldUnitVal(r,'maximum'),experience:bldUnitVal(r,'experience')};
  if(!bldStagePool(r.twin,r.twin_level,pool,null))
    return toast(tt('buildings.is_already_in',{unit:c.unit,twin:r.twin,x:r.twin_level_label||r.twin_level}));
  r.twin_has=true;                    // the panel is looking at staged state now
  bldTouched(); bldUnitRender();
  toast(tt('buildings.staged_into_saved_with_the_rest',{unit:c.unit,twin:r.twin,x:r.twin_level_label||r.twin_level}),4200);
}
function bldUnitApply(){
  const b=state.bld,c=b.cmp;
  const dirty=bldUnitDirtyRows();
  if(!dirty.length)return;
  let here=0,elsewhere=0;
  for(const r of dirty){
    const e=c.edits[r.cap_line];
    const pool={unit:r.unit||c.unit,
      initial:e.initial!==undefined?e.initial:r.initial,
      per_turn:e.per_turn!==undefined?e.per_turn:r.per_turn,
      maximum:e.maximum!==undefined?e.maximum:r.maximum,
      experience:e.experience!==undefined?e.experience:r.experience};
    if(r.line===b.line){
      // the building on screen already has this row in its working copy, found
      // by the EDB line it came from - edit it there so the form stays truthful
      const row=[...b.work.levels[r.level_index].caps,...b.work.levels[r.level_index].fcaps]
        .find(x=>x.line===r.cap_line);
      if(row&&row.pool){
        Object.assign(row.pool,pool);
        if(e.condEdited){row.conds=e.conds;row.condEdited=true;row.requires=e.requires;}
        here++; continue;
      }
    }
    // a row in another line: staged by the EDB line index it already occupies,
    // which is what the server's capability planner keys an in-place rewrite on
    const rows=bldAlso(r.line,r.level);
    const prev=rows.find(x=>x.line===r.cap_line);
    if(prev){
      Object.assign(prev.pool,pool);
      if(e.condEdited){prev.conds=e.conds;prev.condEdited=true;prev.requires=e.requires;}
    }
    else rows.push({line:r.cap_line,keyword:'recruit_pool',args:'',
      requires:e.condEdited?e.requires:(r.requires||''),
      conds:e.condEdited?e.conds:[],condEdited:!!e.condEdited,bonus:false,value:'',
      pool:Object.assign({},pool),comment:'',faction:!!r.faction,del:false});
    elsewhere++;
  }
  c.edits={};
  bldPickCancel();                   // back to the building editor
  bldTouched(); renderBuildingEditor();
  toast(tt('buildings.pool_s_staged',{x:here+elsewhere,elsewhere:elsewhere?tt('buildings.of_them_in_other_building_line',{elsewhere}):''}),4200);
}

/* ---- hop to the Unit Editor and back ----
   The building editor's whole state (which line, which level, every unsaved
   edit) lives in state.bld, which nothing here clears - so coming back is just
   re-rendering it. bldReturn only records what the Back button should say and
   which level to land on. */
function openUnitFromBuilding(type){
  const b=state.bld;
  if(bldDirty()&&!confirm(
      tt('buildings.unsaved_changes_switch_to_unit_editor')))return;
  state.bldReturn={line:b.line,lvl:b.lvl,label:b.d.label};
  closeModal();
  state.mode='edit';
  applyMode(true);
  openEditor(type);
}
async function backToBuilding(){
  const r=state.bldReturn,b=state.bld; if(!r||!b)return;
  if(state.ed&&(edDirty()||edCmpDirty()||edRecDirty())
     &&!confirm(tt('buildings.discard_the_unsaved_unit_changes_and')))return;
  state.ed=null; closeModal();
  state.bldReturn=null;
  state.mode='buildings';
  applyMode(true);
  // The working copy is NOT rebuilt: everything typed into the building before
  // the hop is still in b.work, and throwing it away is exactly what makes
  // switching back and forth useless. Only the read-only half is re-read, so a
  // unit renamed or deleted in the meantime shows up as such in the pool rows.
  // Capability line numbers index the EDB, which a unit edit never touches, so
  // the working copy stays valid against it.
  if(b.work&&b.line===r.line){
    b.lvl=r.lvl;
    try{
      const fresh=await api.get(`/api/building?mod=${enc(b.mod)}&line=${enc(r.line)}`);
      if(fresh.levels.length===b.work.levels.length)b.d=fresh;
    }catch(e){}
    b.planStale=!!b.plan;
    document.getElementById('modal').className='modal wide';
    overlay.classList.add('open');
    renderBuildingEditor();
    return;
  }
  b.lvl=r.lvl;
  await openBuilding(r.line,true);
}

/* ---- preview / save ---- */
function bldPayload(){
  const b=state.bld;
  const origLevels=JSON.parse(b.orig).levels;
  return {mod:b.mod,line:b.line,fix_ownership:b.fixOwnership!==false,
    // A line hand-edited as text replaces its whole block, and the boxes then
    // apply on top of it. Sent from the first hand edit onwards even if the text
    // has since been typed back to what the file says: the capability rows now
    // count lines from the pane's text, and only the raw path plans against it.
    raw_block:bldCvOwns()?bldCvOf().base:'',
    levels:b.work.levels.map((lv,i)=>{
    const o=origLevels[i],out={name:lv.name,settlement:lv.settlement,requires:lv.requires,
      scalars:lv.scalars,upgrades:lv.upgrades,
      capabilities:[...lv.caps].map(bldCapOp),
      faction_capabilities:[...lv.fcaps].map(bldCapOp)};
    if(lv.condEdited)out.conditions=lv.conds;
    // Only send the localisation records whose text actually changed: their
    // presence is what makes the server rewrite text/export_buildings.txt at
    // all. `loc` is the shared key, `loc_cultures` the per-culture ones.
    const was=o.locAll||{},cultures={};
    for(const c of Object.keys(lv.locAll||{})){
      const rec=lv.locAll[c],old=was[c]||{};
      if(rec.name===(old.name||'')&&rec.descr===(old.descr||'')
         &&rec.descr_short===(old.descr_short||''))continue;
      const send={name:rec.name||'',descr:rec.descr||'',descr_short:rec.descr_short||''};
      if(c)cultures[c]=send; else out.loc=send;
    }
    if(Object.keys(cultures).length)out.loc_cultures=cultures;
    return out;}),
    // Rows staged against other building lines - the castle twin, or every tree
    // that trains one unit. Planned against the same parse and spliced in the
    // same pass, so this stays one edit and one undo step.
    also:Object.entries((b.work.also)||{}).map(([line,byLevel])=>({
      line,
      levels:Object.entries(byLevel).filter(([,rows])=>rows.length)
        .map(([name,rows])=>({name,capabilities:rows.map(bldCapOp)}))
    })).filter(x=>x.levels.length)};
}
function bldCapOp(c){
  const args=c.pool
    ? `"${c.pool.unit}"  ${c.pool.initial}  ${c.pool.per_turn}  ${c.pool.maximum}  ${c.pool.experience}`
    : ((c.bonus?'bonus ':'')+(c.value||'')).trim();
  const op={line:c.line,keyword:c.keyword,args,requires:c.requires,delete:!!c.del};
  // Structure only where the clause was actually built here. A row copied from
  // somewhere else is new but its clause is not: it carries the original text,
  // and re-emitting that from structure would quietly re-tidy - or, for a row
  // with no parsed conditions, silently drop - a clause nobody edited.
  if(c.condEdited)op.conditions=c.conds||[];
  return op;
}
async function bldPreview(){
  const b=state.bld;
  const box=document.getElementById('bldPlan');
  await cvSettle(b.cv);                 // read the last keystroke before planning
  const blocked=bldCvBlocked();
  if(blocked){box.innerHTML=`<div class="mbody w-bad">${esc(blocked)}</div>`; return;}
  box.innerHTML=`<div class="count" style="padding:8px">${tt('common.working_out_what_would_change')}</div>`;
  try{
    b.plan=await api.post('/api/buildings/plan',bldPayload());
    b.planStale=false;
    box.innerHTML=bldPlanHtml(b.plan,false);
  }catch(e){ box.innerHTML=`<div class="mbody w-bad">${esc(errText(e))}</div>`; }
}
function bldPlanHtml(p,stale,fold='bld.probe'){
  if(p.error)return `<div class="sum"><div class="srow bad"><span class="sicon">✕</span>
    <span class="stext">${esc(p.error)}</span></div></div>`;
  const rows=[];
  (p.changes||[]).forEach(c=>rows.push(`<div class="srow"><span class="sicon">•</span>
    <span class="stext">${esc(c)}</span></div>`));
  (p.warnings||[]).forEach(c=>rows.push(`<div class="srow warn"><span class="sicon">!</span>
    <span class="stext">${esc(c)}</span></div>`));
  (p.errors||[]).forEach(c=>rows.push(`<div class="srow bad"><span class="sicon">✕</span>
    <span class="stext">${esc(c)}</span></div>`));
  if(!rows.length)rows.push(`<div class="srow"><span class="sicon">·</span>
    <span class="stext">${tt('buildings.nothing_would_change')}</span></div>`);
  const files=[p.edb_rewritten?'export_descr_buildings.txt':'',
               p.loc_rewritten?'text/export_buildings.txt':'',
               p.edu_rewritten?'export_descr_unit.txt':'',
               p.modeldb_rewritten?'unit_models/battle_models.modeldb':''].filter(Boolean);
  // folded like the lists above it, with what it found counted on the heading
  const tally=[[(p.changes||[]).length,'buildings.change_count'],[(p.warnings||[]).length,'buildings.warning_count'],
    [(p.errors||[]).length,'buildings.error_count']].filter(([n])=>n).map(([n,id])=>ttN(id,n));
  return `<div class="bsec ${foldCls(fold)}" data-fold="${fold}" style="margin-top:14px"><h4>${tt('buildings.probe',{tally:tally.length?` <span class="count">${tally.join(' · ')}</span>`:'',stale:stale?` <span class="w-warn">${tt('buildings.out_of_date_edited_since')}</span>`:''})}</h4>
    <div class="sum">${rows.join('')}
      ${files.length?`<div class="srow shead" style="margin-top:6px"><span class="sicon">→</span>
        <span class="stext">${tt('buildings.writes',{x:files.map(f=>`<code>${esc(f)}</code>`)
          .join(files.length>2?', ':' and ')})}</span></div>`:''}
    </div></div>`;
}
async function bldSave(){
  const b=state.bld;
  await cvSettle(b.cv);                 // the last keystroke counts
  const blocked=bldCvBlocked();
  if(blocked){toast(blocked,6000); return;}
  if(!bldDirty()){toast(tt('buildings.nothing_to_save'));return;}
  const btn=event&&event.target; if(btn)btn.disabled=true;
  try{
    const res=await api.post('/api/buildings/apply',
      Object.assign(bldPayload(),{clear_strings_bin:clearBinOn()}));
    if(res.error){ toast(res.error,5000);
      document.getElementById('bldPlan').innerHTML=bldPlanHtml(res.plan||{error:res.error},false);
      return; }
    toast(tt('buildings.saved_change_s_written_to',{n:(res.plan.changes||[]).length,mod:b.mod}));
    state.bld.ov=await api.get('/api/buildings?mod='+enc(state.src));
    _bldFiltersFor='';
    await openBuilding(b.line,true);           // re-read from disk, keep the level
    render();
  }catch(e){ toast(tt('buildings.save_failed_error',{error:e}),5000); }
  finally{ if(btn)btn.disabled=false; }
}

/* ========================= a new building tree =========================
   The one thing the Buildings screen could not do: every other operation here
   edits a line that is already in the file. A tree is three things at once -
   the EDB block, three text keys per level, and the per-culture cards - and the
   first two have to land together, because a level with no `{name}` key crashes
   the game at the construction panel (all 1099 levels in the three installed
   mods have all three of theirs). The cards are art and stay yours to draw; the
   dialog lists the paths and calls a blank one a blank, not a fault.

   Same plan → preview → apply road as every other save here, through the same
   two endpoints: the server owns the block's text, so what the preview counts
   and what Create writes cannot be two different things.

   THE LEVELS CHAIN FORWARD. Each one's `upgrades` block names the next and never
   the other way about - all 771 upgrade entries measured across the three mods
   point at a level listed later on the `levels` line, which is what TWCenter's
   hardcoded-limits note says the engine requires. */

const NT_MAX_ROWS=20;
const bldNt=()=>state.bld&&state.bld.nt;
const bldNtName=()=>{const n=bldNt(); return (n.prefix||'')+(n.stem||'').trim();};
const bldNtDefaultLabel=name=>(name||'').replace(/_/g,' ')
  .replace(/\b\w/g,c=>c.toUpperCase());

function bldNewTree(){
  const b=state.bld;
  b.nt={prefix:'',stem:'',label:'',settlement:'city',religion:'',convert_to:'',
        levels:[{name:'',label:'',auto:true},{name:'',label:'',auto:true},
                {name:'',label:'',auto:true}],
        plan:null,busy:false};
  bldNtRenumber();
  overlay.classList.add('open');
  document.getElementById('modal').className='modal wide';
  bldNtPaint();
}
/* A level whose name you have not touched follows the line's - type `forge` and
   the three rows become forge_1, forge_2, forge_3. Touch one and it stops
   following, because renaming it back under you is the worse failure. */
function bldNtRenumber(){
  const n=bldNt(),base=bldNtName();
  n.levels.forEach((lv,i)=>{ if(lv.auto)lv.name=base?base+'_'+(i+1):''; });
}
function bldNtSet(key,value){
  const n=bldNt();
  bldNtRead();
  n[key]=value;
  if(key==='prefix'||key==='stem')bldNtRenumber();
  n.plan=null;
  bldNtPaint();
}
// A keystroke drops the stale preview but does NOT repaint: rebuilding the form
// under the caret would lose the cursor position on every character typed.
function bldNtTouch(i,key,value){
  const n=bldNt();
  if(i>=0){
    const lv=n.levels[i]; if(!lv)return;
    lv[key]=value;
    if(key==='name')lv.auto=false;
  }else{
    n[key]=value;
    if(key==='stem'){
      bldNtRenumber();
      n.levels.forEach((lv,j)=>{
        if(!lv.auto)return;
        const box=document.getElementById('ntN'+j); if(box)box.value=lv.name;
        const lab=document.getElementById('ntL'+j);
        if(lab)lab.placeholder=bldNtDefaultLabel(lv.name);
      });
    }
  }
  n.plan=null;
  document.getElementById('ntPlan').innerHTML=bldNtHint();
}
function bldNtAddLevel(){
  const n=bldNt();
  if(n.levels.length>=NT_MAX_ROWS)return;
  bldNtRead();
  n.levels.push({name:'',label:'',auto:true});
  bldNtRenumber(); n.plan=null; bldNtPaint();
}
function bldNtDropLevel(i){
  const n=bldNt();
  if(n.levels.length<=1)return;
  bldNtRead();
  n.levels.splice(i,1);
  bldNtRenumber(); n.plan=null; bldNtPaint();
}
// Pull every box back into the form state before a repaint or a request.
function bldNtRead(){
  const n=bldNt(); if(!n)return;
  const get=id=>{const el=document.getElementById(id); return el?el.value:undefined;};
  const stem=get('ntStem'); if(stem!==undefined)n.stem=stem;
  const label=get('ntLabel'); if(label!==undefined)n.label=label;
  n.levels.forEach((lv,i)=>{
    const nm=get('ntN'+i); if(nm!==undefined&&nm!==lv.name){lv.name=nm; lv.auto=false;}
    const lb=get('ntL'+i); if(lb!==undefined)lv.label=lb;
  });
}
function bldNtSpec(){
  const n=bldNt();
  return {name:bldNtName(),label:(n.label||'').trim(),
          settlement:n.settlement,religion:n.religion,convert_to:n.convert_to,
          levels:n.levels.map(lv=>({name:(lv.name||'').trim(),
                                    label:(lv.label||'').trim()}))};
}
function bldNtHint(){
  const n=bldNt(),name=bldNtName();
  if(!name)return `<div class="bnote">${tt('buildings.give_the_line_a_name_to')}</div>`;
  const kept=n.levels.map(x=>(x.name||'').trim()).filter(Boolean);
  return `<div class="bnote">${docPoints(tt('buildings.what_create_would_write'),[
    ttN('buildings.building_with_levels_at_the_end',kept.length,{name:esc(name)}),
    ttN('buildings.text_keys_in_export_buildings',kept.length*3),
    tt('buildings.probe_first_nothing_is_written_until')])}</div>`;
}
function bldNtPaint(){
  const b=state.bld,ov=b.ov,n=b.nt;
  const prefixes=ov.prefixes||[{prefix:'',label:tt('buildings.no_prefix'),hint:''}];
  const chosen=prefixes.find(p=>p.prefix===n.prefix)||prefixes[0];
  document.getElementById('modal').innerHTML=`<h2>${tt('buildings.new_building_tree_in',{mod:esc(b.mod)})}</h2>
    <div class="mbody">
      <div class="brow">
        <label style="flex:0 0 180px">${tt('buildings.prefix')}
          <select onchange="bldNtSet('prefix',this.value)">
            ${prefixes.map(p=>`<option value="${esc(p.prefix)}" ${
              p.prefix===n.prefix?'selected':''}>${esc(p.label)}</option>`).join('')}
          </select></label>
        <label style="flex:1 1 200px">${tt('buildings.line_name_the_code_name')}
          <input id="ntStem" value="${esc(n.stem)}" placeholder="${ttA('buildings.forge')}"
            oninput="bldNtTouch(-1,'stem',this.value)"></label>
        <label style="flex:1 1 200px">${tt('buildings.shown_as')}
          <input id="ntLabel" value="${esc(n.label)}" placeholder="${ttA('buildings.forge_2')}"
            oninput="bldNtTouch(-1,'label',this.value)"></label>
      </div>
      ${chosen&&chosen.hint?`<div class="bnote">${esc(chosen.hint)}</div>`:''}
      <div class="brow">
        <label style="flex:0 0 180px">${tt('common.settlement')}
          <select onchange="bldNtSet('settlement',this.value)">
            <option value="city" ${n.settlement==='city'?'selected':''}>${tt('buildings.city')}</option>
            <option value="castle" ${n.settlement==='castle'?'selected':''}>${tt('buildings.castle')}</option>
            <option value="" ${n.settlement===''?'selected':''}>${tt('buildings.both_no_word_on_the_line')}</option>
          </select></label>
        <label style="flex:0 0 180px">${tt('buildings.religion_2')}
          <select onchange="bldNtSet('religion',this.value)">
            <option value="">(none)</option>
            ${(ov.religions||[]).map(r=>`<option value="${esc(r)}" ${
              r===n.religion?'selected':''}>${esc(r)}</option>`).join('')}
          </select></label>
        <label style="flex:1 1 220px">${tt('buildings.converts_to_the_twin_line')}
          <select onchange="bldNtSet('convert_to',this.value)">
            <option value="">(none)</option>
            ${(ov.lines||[]).map(l=>`<option value="${esc(l.name)}" ${
              l.name===n.convert_to?'selected':''}>${esc(l.name)}</option>`).join('')}
          </select></label>
      </div>

      <div class="bsec"><h4>${tt('buildings.levels_each_one_upgrades_into_the',{levels_n:n.levels.length})}
          <button style="margin-left:auto" onclick="bldNtAddLevel()"
            ${n.levels.length>=NT_MAX_ROWS?'disabled':''}>${tt('buildings.add_level')}</button></h4>
        <div class="ntlv"><span class="i"></span>${tt('buildings.code_name_shown_as')}</div>
        ${n.levels.map((lv,i)=>`<div class="ntlv">
          <span class="i">${i+1}</span>
          <input id="ntN${i}" value="${esc(lv.name)}" placeholder="${ttA('buildings.code_name')}"
            oninput="bldNtTouch(${i},'name',this.value)">
          <input id="ntL${i}" value="${esc(lv.label)}"
            placeholder="${esc(bldNtDefaultLabel(lv.name))}"
            oninput="bldNtTouch(${i},'label',this.value)">
          <button class="x danger" title="${ttA('buildings.remove_this_level')}"
            ${n.levels.length<=1?'disabled':''} onclick="bldNtDropLevel(${i})">🗑</button>
        </div>`).join('')}
        <div class="bnote">${docPoints(tt('buildings.every_level_starts_from_the_same'),[
          tt('buildings.an_empty_capability_block_and_material'),
          tt('buildings.a_build_time_and_a_cost'),
          tt('buildings.requires_factions_naming_every_culture'),
          tt('buildings.units_come_after_open_the_line')])}</div>
      </div>

      <div id="ntPlan">${bldNtHint()}</div>
    </div>
    <div class="foot">
      <button onclick="bldNtCancel()">${tt('common.cancel')}</button>
      <button onclick="bldNtPreview()">${tt('common.probe')}</button>
      <button class="primary" onclick="bldNtCreate()">${tt('common.create')}</button>
    </div>`;
  if(n.plan)document.getElementById('ntPlan').innerHTML=bldNtPlanHtml(n.plan);
}
function bldNtCancel(){ state.bld.nt=null; closeModal(); }

function bldNtPlanHtml(p){
  const slots=(p.slots||[]).filter(s=>!s.found);
  if(!slots.length)return bldPlanHtml(p,false);
  return bldPlanHtml(p,false)+`<div class="bsec"><h4>${tt('buildings.building_cards_to_draw')}
      <span class="n">${slots.length}</span></h4>
    <div class="ntslots">${slots.map(s=>`<div><code>${esc(s.small)}</code>${
      s.large_found?'':` · <code>${esc(s.large)}</code>`}</div>`).join('')}</div>
    <div class="bnote">${docPoints(tt('buildings.a_list_to_draw_against_not'),[
      tt('buildings.78_62_tga_for_the_button'),
      tt('buildings.a_level_with_no_card_is')])}</div></div>`;
}
async function bldNtPreview(){
  const n=bldNt(); if(!n)return;
  bldNtRead();
  const box=document.getElementById('ntPlan');
  box.innerHTML=`<div class="count" style="padding:8px">${tt('buildings.working_out_what_would_be_written')}</div>`;
  try{
    n.plan=await api.post('/api/buildings/plan',{mod:state.src,create:bldNtSpec()});
    box.innerHTML=bldNtPlanHtml(n.plan);
  }catch(e){ box.innerHTML=`<div class="mbody w-bad">${esc(errText(e))}</div>`; }
}
async function bldNtCreate(){
  const n=bldNt(); if(!n||n.busy)return;
  bldNtRead();
  const name=bldNtName();
  const btn=event&&event.target; if(btn)btn.disabled=true;
  n.busy=true;
  try{
    const res=await api.post('/api/buildings/apply',
      {mod:state.src,create:bldNtSpec(),clear_strings_bin:clearBinOn()});
    if(res.error){
      n.plan=res.plan||{error:res.error};
      document.getElementById('ntPlan').innerHTML=bldNtPlanHtml(n.plan);
      toast(res.error,6000);
      return;
    }
    toast(tt('buildings.created_change_s_written_to',{name,n:(res.plan.changes||[]).length,src:state.src}));
    state.bld.nt=null;
    // the EDB is a different file now, so the overview is re-read rather than patched
    await loadBuildings(true);
    bldOpenTrees().add(name);
    _bldFiltersFor='';
    render();                       // the list behind the dialog gained a row
    await openBuilding(name);       // …and the new line opens on top of it
  }catch(e){ toast(tt('buildings.create_failed_error',{error:e}),6000); }
  finally{ if(btn)btn.disabled=false; if(bldNt())bldNt().busy=false; }
}
