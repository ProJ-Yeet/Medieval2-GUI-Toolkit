/* edrecruit.js - the unit editor's Recruitment tab: every building that trains
   this unit, editable in place, and the ＋ that adds it to one more

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ===================== RECRUITMENT (unit editor tab) =====================
   The last thing about a unit that lived somewhere else. Everything a unit IS
   is on the other four tabs; where it can be HIRED was in another module
   entirely, reached by leaving the unit, finding one of the four or five
   building lines that train it, and reading its numbers off a row among sixty.
   The building browser already had the panel that puts them side by side
   (`bldShowUnit`) - this is that view, from the unit's side, and editing.

   Three things make it a tab rather than a link to that panel:

     * **it is reached from the unit.** No building has to be open, so there is
       no `state.bld.work` under it and nothing to stage into. The edits are
       their own bucket on `state.ed`, and Save writes them through
       `/api/buildings/apply` as one pass over the EDB - beside the unit's own
       save, never inside it, because they are different files.
     * **a building is a click away, in its own tab.** The row's name opens the
       Buildings module at that line, on that tier, with the unit's rows
       flashed (`?building=&lvl=&unit=`, handled in core.js's `init`). A new
       browser tab, like every other "go and look at that" link in the editor,
       so the unit you were editing is still open behind you.
     * **it can add one.** "This unit is not recruitable anywhere" and "it is
       recruitable in three places and I want a fourth" were both a trip to the
       Buildings module. The ＋ picker lists every line in the mod and every
       tier in it, and what it stages rides the same Save.

   What it does NOT do is own the file: a `recruit_pool` line is written by
   `unittransfer/buildings.py` exactly as the building editor writes it (the
   same `capabilities` ops, the same clause dialog, the same plan → apply road),
   so a pool edited from here and one edited from there cannot drift apart. */

//: The four numbers of a pool, in the order the `recruit_pool` line writes them.
const ED_REC_KEYS=['initial','per_turn','maximum','experience'];
// Whitespace-only differences are not edits - the clause editor re-emits with
// one space where the file often has three. Same test the server applies.
const edRecNorm=s=>String(s==null?'':s).replace(/\s+/g,' ').trim();
const edRecOn=()=>(state.ed&&state.ed.rec)||null;
const edRecRows=()=>{const r=edRecOn();return (r&&r.r&&r.r.instances)||[];};
// A row's identity is the EDB line its `recruit_pool` occupies: unique across
// the whole file, and the very thing the server keys an in-place rewrite on.
const edRecKey=row=>row.cap_line;

/* ---- loading ----
   Two requests, and the overview is not optional: it carries the building list
   the ＋ picker offers AND the `requires` vocabulary the clause dialog is built
   from, both of which live on `state.bld`. Loading it here is why the Buildings
   module opens instantly after a visit to this tab. */
async function edRecLoad(force){
  const e=state.ed; if(!e)return;
  if(e.rec&&!force)return;
  const rec={loading:true,error:'',r:null,edits:{},dels:[],adds:[],pick:null};
  e.rec=rec;
  edRecRedraw();
  try{
    await loadBuildings();
    const r=await api.get(`/api/buildings/unit?mod=${enc(e.mod)}&type=${enc(e.unit)}`
                          +`&culture=${enc((state.bld&&state.bld.culture)||'')}`);
    if(r.error)rec.error=r.error; else rec.r=r;
  }catch(err){ rec.error=errText(err); }
  rec.loading=false;
  // the dialog may have been closed, or moved to another unit, while this was out
  if(state.ed&&state.ed.rec===rec)edRecRedraw();
}
/* Repaint whatever of this tab is on screen - which may be none of it.
   The load is also kicked off from `edRecReload` after a save, and the modal is
   showing the "Saving…" card then: there is no tab body to write into, and the
   editor is rebuilt whole a moment later anyway. */
function edRecRedraw(){
  if(!state.ed)return;
  if(state.ed.tab==='recruit'&&document.getElementById('edBody'))edRenderTab();
  else edRecPaintTab();
}

/* ---- what the panel currently has ---- */
function edRecEdit(row){
  const r=edRecOn();
  return r.edits[edRecKey(row)]||(r.edits[edRecKey(row)]={});
}
function edRecVal(row,key){
  const e=(edRecOn().edits[edRecKey(row)])||{};
  return e[key]!==undefined?e[key]:row[key];
}
function edRecSet(row,key,val){
  edRecEdit(row)[key]=val;
  paintDirty();
}
// The clause as this panel has it: an edited one wins over the file's text.
function edRecReq(row){
  const e=edRecOn().edits[edRecKey(row)];
  return (e&&e.condEdited)?(e.requires||''):(row.requires||'');
}
const edRecDeleted=row=>edRecOn().dels.includes(edRecKey(row));
function edRecToggleDel(capLine){
  const r=edRecOn(),i=r.dels.indexOf(capLine);
  if(i<0)r.dels.push(capLine); else r.dels.splice(i,1);
  edRenderTab();
}
function edRecDropAdd(i){
  edRecOn().adds.splice(i,1);
  edRenderTab();
}

/* ---- is there anything to write ---- */
function edRecRowDirty(row){
  const r=edRecOn(),e=r.edits[edRecKey(row)];
  if(r.dels.includes(edRecKey(row)))return true;
  if(!e)return false;
  if(e.condEdited&&edRecNorm(e.requires)!==edRecNorm(row.requires))return true;
  return ED_REC_KEYS.some(k=>e[k]!==undefined&&String(e[k]).trim()!==String(row[k]).trim());
}
function edRecDirty(){
  const r=edRecOn(); if(!r||!r.r)return false;
  return !!(r.adds.length||edRecRows().some(edRecRowDirty));
}
function edRecChangeCount(){
  const r=edRecOn(); if(!r||!r.r)return 0;
  return r.adds.length+edRecRows().filter(edRecRowDirty).length;
}

/* ---- open the building itself ----
   Its own browser tab, because this one holds unsaved unit edits and the
   building is being opened to LOOK at - the same reasoning as `openUnitTab`.
   `lvl` lands on the tier the pool is on and `unit` flashes its rows there; a
   recruitment edit staged here is not in that tab, and the hint under the table
   says so rather than pretending the two are one document. */
function edRecOpenBuilding(line,levelIndex){
  const e=state.ed;
  window.open(`/?mod=${enc(e.mod)}&building=${enc(line)}&lvl=${enc(levelIndex)}`
              +`&unit=${enc(e.unit)}`,'_blank');
}

/* ---- whose art a row wears ----
   A pool is not shown "in a culture" here: the rows come from every building
   line in the mod, and the tier they name is drawn once per culture that builds
   it. The row's OWN `requires` is the answer where it has one - a pool gated to
   `factions { aztecs, }` is Dunlending, so it wears the Dunlending stable - and
   the browser's current culture is the fallback for a pool open to everyone.
   `bldIcon`'s `any` flag catches the rest: a mod-invented level like DaC's
   `ancestral_dun` exists in exactly one culture's folder, and a placeholder
   would be claiming the building has no art when it plainly has. */
function edRecCulture(conds){
  const fc=(state.bld&&state.bld.ov&&state.bld.ov.faction_cultures)||{};
  const facs=(conds||[]).filter(x=>x.kind==='factions'&&!x.negate)
                        .reduce((a,x)=>a.concat(x.values||[]),[]);
  for(const f of facs){
    const k=String(f||'').toLowerCase();
    // a clause names factions, but a mod may write the culture's own name there
    if(fc[k])return fc[k];
    if(Object.keys(fc).some(x=>fc[x]===k))return k;
  }
  return bldCultureNow();
}

/* ---- editing a pool's `requires` ----
   The building editor's own clause dialog, given a host of our own: these rows
   come from a dozen building blocks, none of them loaded into a working copy,
   so there is no capability object to hand it. The edit lands in the same
   bucket as the numbers and is written by the same Save, which is what makes a
   requirement edited here save exactly like one edited from the building.

   It does NOT go through `bldClauseStash`: that stashes the modal as MARKUP,
   and the unit editor's 3D column is a live WebGL canvas inside it - restoring
   the string would put back a dead copy and orphan the real one. Coming back
   re-renders the editor from state instead, which hands the column over
   properly (`edPrevAttach`). See `bldClauseApply` / `bldClauseCancel`. */
function edRecEditReq(kind,id){
  const r=edRecOn();
  // the dialog is built out of the building overview's vocabulary, so it cannot
  // open before that has arrived - which, having drawn a row, it has
  if(!r||!state.bld||!state.bld.ov)return;
  let host;
  const unit=state.ed.unit;
  if(kind==='add'){ host=r.adds[id]; if(!host)return; }
  else{
    const row=edRecRows().find(x=>edRecKey(x)===id); if(!row)return;
    host=edRecEdit(row);
    if(!host.condEdited)host.conds=JSON.parse(JSON.stringify(row.conditions||[]));
  }
  const conds=host.conds||[];
  state.bld.clause={host,kind:'edrec',index:id,unit,units:[unit],pick:null,
                    conds:JSON.parse(JSON.stringify(conds)),
                    was:JSON.parse(JSON.stringify(conds))};
  edPrevDetach();                     // the live column must not go with the markup
  renderClauseDialog();
  bldClauseOwnership();
}

/* ======================== the tab ======================== */
function edRecTabLabel(){
  const r=edRecOn();
  const n=(r&&r.r)?r.r.instances.length+r.adds.length:null;
  return 'Recruitment'+(n===null?'':` <span class="badge">${n}</span>`);
}
function edRecTab(){
  const e=state.ed,r=e.rec;
  // The first paint of this tab is what asks for the data; a microtask rather
  // than a call from inside the render, which would re-enter it.
  if(!r){ Promise.resolve().then(()=>edRecLoad()); return edRecBusy(); }
  if(r.loading)return edRecBusy();
  if(r.error)return `<div class="frm"><div class="w-bad">${esc(r.error)}</div>
    <div class="bnote">Recruitment is read from <code>data/export_descr_buildings.txt</code>.
      A mod without one has nothing to show here.</div></div>`;
  const rows=edRecRows();
  //: The EDU/EDB keyword on the left, what the column is CALLED on the right -
  //: the same names every other screen in the toolkit gives these four numbers.
  const KEYS=[['initial',POOL_LABEL.initial],['per_turn',POOL_LABEL.per_turn],
              ['maximum',POOL_LABEL.maximum],['experience',POOL_SHORT.experience]];
  // A value that is not the one most of the pools use is what you came here to
  // find, so it is marked rather than left to be spotted.
  const common=KEYS.map(([k])=>{
    const tally={};
    rows.forEach(row=>{const v=String(edRecVal(row,k)).trim();tally[v]=(tally[v]||0)+1;});
    return (Object.entries(tally).sort((x,y)=>y[1]-x[1])[0]||['',0])[0];
  });
  return `<div class="frm">
    <div class="brow" style="align-items:center">
      <b>${rows.length} recruit pool${rows.length===1?'':'s'}</b>${r.adds.length
        ? ` <span class="badge good">+${r.adds.length} staged</span>`:''}
      <span class="count">${rows.length
        ? 'Every building line in this mod that trains this unit.'
        : 'No building line in this mod trains this unit.'}</span>
      <button class="primary" style="margin-left:auto"
        onclick="edRecAddOpen()">＋ Add a building…</button>
    </div>
    ${e.newType&&e.newType!==e.d.type?`<div class="ownwarn" style="margin:10px 0 0">
      Renaming the unit to <code>${esc(e.newType)}</code> rewrites these pools as part of the
      <b>unit</b> save. The rows below still name <code>${esc(e.d.type)}</code>, which is what a
      recruitment change written now would use - save the rename first if you are doing both.
    </div>`:''}
    ${rows.length||r.adds.length?`<div class="poollist" id="edRecList" style="margin-top:10px">
      <div class="erhd"><span class="erb">Building</span><span class="erlv">Tier</span>
        <span class="ernums">${KEYS.map(([k,l])=>
          `<span class="ern" title="${esc(POOL_HELP[k]||'')}">${esc(l)}</span>`).join('')}</span>
        <span class="eract"></span></div>
      ${rows.map(row=>edRecRowHtml(row,KEYS,common)).join('')}
      ${r.adds.map((a,i)=>edRecAddRowHtml(a,i,KEYS)).join('')}
    </div>`:''}
    <div class="bnote" style="margin-top:8px">${docPoints(
      'These are the same <code>recruit_pool</code> lines the Buildings module edits, written by the same save.',[
      // the first two describe rows, so they are dropped when there are none
      rows.length&&'A tier is shown as its position in its own line, so tier 2 of a three-level '
        +'barracks and tier 2 of a five-level one are both “2”. The <b>odd</b> mark is a value '
        +'that disagrees with what most of the other pools use.',
      (rows.length||r.adds.length)&&'The building’s name opens it in a <b>new browser tab</b>, on '
        +'that tier, with this unit’s rows flashed. That tab reads the file - changes staged here '
        +'are not in it until you save.',
      '<b>Save changes</b> writes these to <code>export_descr_buildings.txt</code> alongside the '
        +'unit’s own save. One 🕑 Log entry, one undo.'])}</div>
  </div>`;
}
const edRecBusy=()=>`<div class="frm"><div class="empty">Reading every building line…</div></div>`;

/* One pool row, in two lines, read as two halves rather than four columns.

   WHAT the pool sits on is the left of the top line - the tier's own art, the
   line's name, and the tier, in that order and touching, because "a barracks"
   and "which barracks" are one answer and not two. The four numbers hold the
   right, at a fixed width so the header labels sit over the boxes they name.

   WHO may use it is the second line, ending where the numbers do: the `requires`
   clause has no natural width - a real one names half a dozen factions and a
   settlement level - so it keeps a line of its own and grows leftwards into it
   as it needs to, rather than squeezing the name it belongs to. That is the
   shape the building editor's own pool rows settled on, and this tab shares the
   modal with the 3D preview column, so it has even less room to argue with.

   Both callers hand it the same fields; what differs is where they came from
   (a `recruit_pool` in the file, or one staged here) and what the button on the
   end does about it. */
function edRecPoolHtml(o){
  return `<div class="erpool ${o.cls}" ${o.attr}>
    <div class="ertop">
      <span class="erb" title="${esc(o.line)}">
        <img class="erico" loading="lazy" onerror="iconRetry(this)" alt=""
          src="${bldIcon(o.level,'small',o.culture,true)}">
        <a class="ulink" title="Open ${esc(o.lineLabel)} in a new browser tab, on this tier"
          onclick="edRecOpenBuilding('${q1(esc(o.line))}',${o.levelIndex})">${esc(o.lineLabel)}</a>
        ${o.badges}</span>
      <span class="erlv count" title="${esc(o.level)}">${esc(o.levelLabel)}
        <span class="count">(${o.levelIndex+1}/${o.levelCount})</span></span>
      <span class="ernums">${o.nums}</span>
      <span class="eract">${o.act}</span>
    </div>
    <div class="erbot"><span class="prk">Requires</span>
      <span class="erreq ${o.reqEdited?'changed':''}" title="${esc(o.req||'no conditions')}">
        <span>${o.req?esc(o.req)
          :'<span class="count">Always - anyone who can build the tier</span>'}</span>
        <button class="reqbtn" title="Edit who can recruit it from this building"
          onclick="${o.reqEdit}">✎</button></span></div></div>`;
}
function edRecRowHtml(row,KEYS,common){
  const gone=edRecDeleted(row), key=edRecKey(row), req=edRecReq(row);
  return edRecPoolHtml({
    cls:gone?'gone':'', attr:`data-erline="${key}"`,
    line:row.line, lineLabel:row.line_label||row.line,
    level:row.level, levelLabel:row.level_label||row.level,
    levelIndex:row.level_index, levelCount:row.level_count,
    culture:edRecCulture(row.conditions),
    badges:`<span class="badge ${row.settlement==='castle'?'cls':''}">${
        esc(row.settlement||'both')}</span>`
      +(row.faction?`<span class="badge"
        title="This pool sits in the level’s faction_capability block">faction</span>`:''),
    nums:KEYS.map(([k],j)=>{
      const v=edRecVal(row,k);
      const odd=String(v).trim()!==common[j];
      return `<span class="ern ${odd?'odd':''}" title="${odd
        ?'differs from what most pools use ('+esc(common[j])+')':''}">${
        numBox(`data-er="${k}" data-erline="${key}"`,v,
               k==='per_turn'?'turns':(k==='experience'?'1':'pool'))}</span>`;
    }).join(''),
    act:`<button class="reqbtn ${gone?'':'danger'}"
      title="${gone?'Keep this recruit pool':'Remove this recruit pool'}"
      onclick="edRecToggleDel(${key})">${gone?'↺':'🗑'}</button>`,
    req, reqEdited:edRecNorm(req)!==edRecNorm(row.requires||''),
    reqEdit:`edRecEditReq('row',${key})`});
}
// A pool that is not in the file yet: the same row, with no `odd` marks (it has
// no value yet to disagree with anything) and a drop rather than a delete.
function edRecAddRowHtml(a,i,KEYS){
  return edRecPoolHtml({
    cls:'fresh', attr:`data-eradd="${i}"`,
    line:a.line, lineLabel:a.line_label||a.line,
    level:a.level, levelLabel:a.level_label||a.level,
    levelIndex:a.level_index, levelCount:a.level_count,
    culture:edRecCulture(a.conds),
    badges:'<span class="badge good">new</span>',
    nums:KEYS.map(([k])=>`<span class="ern">${
      numBox(`data-eradd="${k}" data-eraddi="${i}"`,a[k],
             k==='per_turn'?'turns':(k==='experience'?'1':'pool'))}</span>`).join(''),
    act:`<button class="reqbtn danger" title="Drop this new pool"
      onclick="edRecDropAdd(${i})">🗑</button>`,
    req:a.requires||'', reqEdited:!!a.condEdited,
    reqEdit:`edRecEditReq('add',${i})`});
}
/* The count on the tab button itself. Adding or dropping a row redraws the tab
   BODY and not the bar above it, and a badge that only catches up on the next
   tab switch is worse than no badge - so the one button is repainted here. */
function edRecPaintTab(){
  const b=document.getElementById('edTab_recruit');
  if(b)b.innerHTML=edRecTabLabel();
}
// Wired from edRenderTab, like every other tab's boxes.
function edWireRecruit(){
  const body=document.getElementById('edBody'); if(!body)return;
  edRecPaintTab();
  wireNumBoxes(body);
  body.querySelectorAll('input[data-er]').forEach(inp=>{
    inp.addEventListener('input',()=>{
      const row=edRecRows().find(x=>edRecKey(x)===+inp.dataset.erline);
      if(row)edRecSet(row,inp.dataset.er,inp.value);
    });
  });
  body.querySelectorAll('input[data-eradd]').forEach(inp=>{
    inp.addEventListener('input',()=>{
      const a=edRecOn().adds[+inp.dataset.eraddi];
      if(a){a[inp.dataset.eradd]=inp.value; paintDirty();}
    });
  });
}

/* ======================== ＋ add a building ========================
   Every line in the mod and every tier in it, because "which building should
   train this" is a question about the whole tree and not about the one that
   happens to be open. A tier the unit is already trained at is shown as such
   and cannot be picked twice - the same refusal `bldStagePool` makes, since a
   unit listed twice in one level is a finding the building checks report.

   The numbers are the dialog's own and are used LITERALLY on every tier picked:
   a pool copied up a line usually grows, but nothing here knows which of the
   tiers you ticked is the bottom of anything, and inventing a climb across two
   unrelated building lines would be a number nobody typed. */
function edRecAddOpen(){
  const r=edRecOn(); if(!r||!r.r)return;
  r.pick={q:'',picked:{},nums:{initial:'1',per_turn:'0.5',maximum:'2',experience:'0'}};
  edPrevDetach();                     // hold the live GL column out of the swap
  edRecAddRender();
}
function edRecAddClose(){
  const r=edRecOn(); if(r)r.pick=null;
  renderEditor();                     // rebuilt from state - nothing to unstash
}
/* Which (line, level) pairs are spoken for: in the file already, or staged.
   Keyed on a NUL between the two names rather than a space - EDB identifiers do
   not carry one, but a key that can be split back apart wrongly is the kind of
   bug that only shows up on somebody else's mod. */
const ED_REC_SEP=String.fromCharCode(0);
const edRecPair=(line,level)=>line+ED_REC_SEP+level;
function edRecTaken(){
  const r=edRecOn(),out={};
  edRecRows().forEach(row=>{ if(!edRecDeleted(row))out[edRecPair(row.line,row.level)]=1; });
  r.adds.forEach(a=>{ out[edRecPair(a.line,a.level)]=2; });
  return out;
}
const edRecLines=()=>((state.bld&&state.bld.ov&&state.bld.ov.lines)||[]);
function edRecAddRender(){
  const e=state.ed,p=e.rec.pick;
  document.getElementById('modal').innerHTML=`
    <h2>Add <span class="pill">${esc(e.loc.name||e.d.type)}</span> to a building</h2>
    <div class="mbody">
      <div class="basebar"><input id="erQ" placeholder="Filter ${esc(e.mod)}’s buildings…"
        value="${esc(p.q)}" oninput="edRecPickFilter(this.value)"></div>
      <div class="baselist" style="max-height:300px" id="erList"></div>
      <div class="bsec" style="margin-top:10px"><h4>Numbers each new pool gets</h4>
        <div class="brow bpnums">
          <label>${qm(POOL_HELP.initial,POOL_LABEL.initial)}${POOL_LABEL.initial}${
            numBox('data-ern="initial"',p.nums.initial,'pool')}</label>
          <label>${qm(POOL_HELP.per_turn,POOL_LABEL.per_turn)}${POOL_LABEL.per_turn}${
            numBox('data-ern="per_turn"',p.nums.per_turn,'turns',
              `<span class="turns">= ${esc(poolTurns(p.nums.per_turn))}</span>`)}</label>
          <label>${qm(POOL_HELP.maximum,POOL_LABEL.maximum)}${POOL_LABEL.maximum}${
            numBox('data-ern="maximum"',p.nums.maximum,'pool')}</label>
          <label>${qm(POOL_HELP.experience,POOL_LABEL.experience)}${POOL_SHORT.experience}${
            numBox('data-ern="experience"',p.nums.experience,'1')}</label>
        </div>
        <div class="bnote">Used as typed on every tier ticked. Each row can be corrected on the
          Recruitment tab before you save, and <b>Requires</b> is set there too - a new pool starts
          with no conditions, which means every faction that can build the tier can hire the unit.</div>
      </div>
    </div>
    <div class="foot"><span class="count" id="erCount"></span>
      <button onclick="edRecAddClose()">Cancel</button>
      <button class="primary" id="erAdd" onclick="edRecAddApply()">Add</button></div>`;
  wireNumBoxes(document.getElementById('modal'));
  document.querySelectorAll('#modal input[data-ern]').forEach(inp=>{
    inp.addEventListener('input',()=>{e.rec.pick.nums[inp.dataset.ern]=inp.value;});
  });
  edRecPickList();
}
function edRecPickFilter(v){ edRecOn().pick.q=v; edRecPickList(); }
// Only the list is redrawn as you type - re-rendering the dialog would take the
// caret out of the filter box.
function edRecPickList(){
  const p=edRecOn().pick,q=p.q.trim().toLowerCase();
  const taken=edRecTaken();
  const lines=edRecLines().filter(l=>!q
    ||l.name.toLowerCase().includes(q)||(l.label||'').toLowerCase().includes(q)
    ||(l.levels||[]).some(n=>n.toLowerCase().includes(q)));
  const box=document.getElementById('erList');
  box.innerHTML=lines.length?lines.map(l=>`<div class="erline">
      <div class="erhead"><img class="erico" loading="lazy" onerror="iconRetry(this)" alt=""
          src="${bldIcon((l.levels||[])[(l.levels||[]).length-1]||l.name,'small','',true)}">
        <b>${esc(l.label||l.name)}</b>
        <code class="count">${esc(l.name)}</code>
        <span class="badge ${l.settlement==='castle'?'cls':''}">${esc(l.settlement||'both')}</span>
        <button style="margin-left:auto" onclick="edRecPickAll('${q1(esc(l.name))}')"
          title="Tick every tier of this line that does not already train the unit">All tiers</button></div>
      <div class="ertiers">${(l.levels||[]).map((lv,i)=>{
        const t=taken[edRecPair(l.name,lv)];
        const on=p.picked[edRecPair(l.name,lv)];
        return `<button class="ertier ${on?'on':''}" ${t?'disabled':''}
          title="${t?(t===2?'Already staged on the Recruitment tab':'This tier already trains the unit')
                   :esc(lv)}"
          onclick="edRecPickTier('${q1(esc(l.name))}','${q1(esc(lv))}')"><img class="erico"
          loading="lazy" onerror="iconRetry(this)" alt=""
          src="${bldIcon(lv,'small','',true)}">${
          i+1}. ${esc((l.level_labels||[])[i]||lv)}${t?' ✓':''}</button>`;
      }).join('')}</div></div>`).join('')
    :`<div class="empty">No building line matches “${esc(p.q)}”.</div>`;
  edRecPickCount();
}
function edRecPickTier(line,level){
  const p=edRecOn().pick,k=edRecPair(line,level);
  if(p.picked[k])delete p.picked[k]; else p.picked[k]=1;
  edRecPickList();
}
function edRecPickAll(line){
  const p=edRecOn().pick,taken=edRecTaken();
  const l=edRecLines().find(x=>x.name===line); if(!l)return;
  const free=(l.levels||[]).filter(lv=>!taken[edRecPair(line,lv)]);
  // one button, both ways: if every free tier is already ticked, untick them
  const all=free.length&&free.every(lv=>p.picked[edRecPair(line,lv)]);
  free.forEach(lv=>{ if(all)delete p.picked[edRecPair(line,lv)];
                     else p.picked[edRecPair(line,lv)]=1; });
  edRecPickList();
}
function edRecPickCount(){
  const n=Object.keys(edRecOn().pick.picked).length;
  const c=document.getElementById('erCount');
  if(c)c.textContent=n?`${n} tier(s) ticked`:'Tick the tiers this unit should be trained at.';
  const b=document.getElementById('erAdd');
  if(b){b.disabled=!n;b.textContent=n?`Add ${n} pool(s)`:'Add';}
}
function edRecAddApply(){
  const r=edRecOn(),p=r.pick;
  const keys=Object.keys(p.picked); if(!keys.length)return;
  keys.forEach(k=>{
    const [line,level]=k.split(ED_REC_SEP);
    const l=edRecLines().find(x=>x.name===line); if(!l)return;
    const i=(l.levels||[]).indexOf(level); if(i<0)return;
    r.adds.push({line,line_label:l.label||line,level,
                 level_label:(l.level_labels||[])[i]||level,
                 level_index:i,level_count:(l.levels||[]).length,
                 initial:p.nums.initial,per_turn:p.nums.per_turn,
                 maximum:p.nums.maximum,experience:p.nums.experience,
                 requires:'',conds:[],condEdited:false});
  });
  r.pick=null;
  renderEditor();
  toast(`${keys.length} recruit pool(s) staged. Save changes writes them.`,4200);
}

/* ======================== saving ========================
   One `/api/buildings/apply` for the lot, however many building lines it
   touches: every line rides in `also`, which the server plans against one parse
   and splices in one pass, so this is one edit and one undo step rather than
   one per building. The main body carries the first line's name (the plan needs
   a line to re-read and check) and no levels of its own - every real edit is in
   `also`, where the recruitment-limit check merges what the file already has
   rather than counting our handful of rows as the whole level. */
function edRecOps(){
  const e=state.ed,r=e.rec,byLine={};
  const unit=e.d.type;
  const args=p=>`"${unit}"  ${p.initial}  ${p.per_turn}  ${p.maximum}  ${p.experience}`;
  const put=(line,level,faction,op)=>{
    const L=byLine[line]||(byLine[line]={});
    const lv=L[level]||(L[level]={capabilities:[],faction_capabilities:[]});
    (faction?lv.faction_capabilities:lv.capabilities).push(op);
  };
  edRecRows().forEach(row=>{
    if(!edRecRowDirty(row))return;
    const ed=r.edits[edRecKey(row)]||{};
    const nums={};
    ED_REC_KEYS.forEach(k=>{nums[k]=edRecVal(row,k);});
    const op={line:edRecKey(row),keyword:'recruit_pool',args:args(nums),
              requires:edRecReq(row),delete:edRecDeleted(row)};
    if(ed.condEdited)op.conditions=ed.conds||[];
    put(row.line,row.level,row.faction,op);
  });
  // A new pool goes in the ordinary `capabilities` block, the same as one added
  // from the building editor: a `faction_capability` is for a line that is only
  // meant to apply to some of them, and this one carries its own clause.
  r.adds.forEach(a=>{
    const op={line:null,keyword:'recruit_pool',args:args(a),
              requires:a.requires||'',delete:false};
    if(a.condEdited)op.conditions=a.conds||[];
    put(a.line,a.level,false,op);
  });
  return byLine;
}
function edRecPayload(extra){
  const e=state.ed,byLine=edRecOps();
  const lines=Object.entries(byLine).map(([line,levels])=>({
    line,
    levels:Object.entries(levels).map(([name,ops])=>{
      const lv={name};
      if(ops.capabilities.length)lv.capabilities=ops.capabilities;
      if(ops.faction_capabilities.length)lv.faction_capabilities=ops.faction_capabilities;
      return lv;
    })}));
  if(!lines.length)return null;
  // `fix_ownership`: a pool naming a faction the unit's EDU `ownership` does not
  // list trains nothing for them, silently. Same default the building editor uses.
  return Object.assign({mod:e.mod,line:lines[0].line,levels:[],
                        fix_ownership:true,also:lines},extra||{});
}
// After the write, the panel is looking at a file it no longer matches - the
// EDB line numbers every row is keyed on have moved. Re-read rather than patch.
async function edRecReload(){
  const e=state.ed; if(!e||!e.rec)return;
  e.rec=null;
  await edRecLoad();
}
