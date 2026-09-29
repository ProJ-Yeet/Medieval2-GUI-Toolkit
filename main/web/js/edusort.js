/* ---- Clean up the unit file -------------------------------------------
   The whole-file counterpart to the Unit Editor: it tidies, tiers, groups and
   reorders every block in export_descr_unit.txt at once.

   Two screens in one dialog. **Clean up** previews what would change, and says
   what the section banners it writes will look like; **Order** lists every unit
   of every section and lets its tier, variant and classification be set from
   there, or the unit dragged to where the sorter should have put it. Nothing is
   written until Apply, and the whole job is one backup and one Undo entry - see
   unittransfer/edusort.py.

   A hand placement is remembered per section and sent back with the next plan,
   so the sorter honours it rather than arguing with it. So are the per-unit
   marks: they go onto each unit's own ;@m2gt line, which is where the next run
   reads them from.

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. */

const eduTidy={mod:'',plan:null,view:'clean',sections:[],hand:{},busy:false,
               // per-unit tier / variant / classification, keyed by unit type
               marks:{},
               // what the drop-downs may offer, sent with the section list
               vocab:{tiers:[],variants:[],specials:[]},
               // How a section banner is drawn. These four values mirror
               // edusort.BANNER_STYLE and are replaced by the server's own copy
               // as soon as the Order tab loads; they are here so the sample on
               // the Clean up tab is right before that happens.
               style:{width:95,fill:'-',prefix:';',upper:false},
               q:'',
               opts:{tidy:true,group:true,banners:true,tiers:true}};

async function openEduTidy(){
  eduTidy.mod=state.src; eduTidy.plan=null; eduTidy.view='clean';
  eduTidy.sections=[]; eduTidy.hand={}; eduTidy.marks={}; eduTidy.q='';
  const modal=document.getElementById('modal');
  modal.className='modal wide';
  modal.innerHTML=`<h2>${tt('edusort.clean_up_the_unit_file')}</h2>`;
  overlay.classList.add('open');
  undoReset();
  renderEduTidy();
  eduTidyPlan();
}

function eduTidyRender(){renderEduTidy();}

function renderEduTidy(){
  const t=eduTidy,p=t.plan;
  const tab=(k,label)=>`<button class="${t.view===k?'on':''}"
    onclick="eduTidyView('${k}')">${label}</button>`;
  document.getElementById('modal').innerHTML=`
    <h2>${tt('edusort.clean_up_the_unit_file')} <span class="pill">${esc(t.mod)}</span></h2>
    <div class="tabs">${tab('clean',tt('common.clean_up'))}${tab('order',tt('edusort.order_and_tiers'))}</div>
    <div class="mbody" id="eduBody">${
      t.view==='clean'?eduTidyClean():eduTidyOrder()}</div>
    <div class="foot">
      <span class="count">${eduTidyMarkCount()?tt('edusort.unit_s_edited_on_the_order',{eduTidyMarkCount:eduTidyMarkCount()}):''}</span>
      <button onclick="closeModal()">${tt('common.close')}</button>
      <button class="primary" ${(!p||!p.touched||p.errors.length||t.busy)?'disabled':''}
        onclick="eduTidyApply()">${t.busy?tt('common.working'):tt('common.apply')}</button>
    </div>`;
  if(t.view==='order')eduTidyWireOrder();
}

function eduTidyView(v){eduTidy.view=v; renderEduTidy();
  if(v==='order'&&!eduTidy.sections.length)eduTidyLoadOrder();}

const eduOpt=(k,label,hint)=>`<label class="chk" title="${esc(hint)}">
  <input type="checkbox" ${eduTidy.opts[k]?'checked':''}
    onchange="eduTidySet('${k}',this.checked)"> ${label}</label>`;

function eduTidySet(k,v){eduTidy.opts[k]=v; eduTidyPlan();}

/* ---- the comment breakers ------------------------------------------------
   The banner above each section is the only text this tool AUTHORS in the unit
   file, so how it looks is the one piece of the result that is a matter of
   taste rather than of format. It was a constant. Now it is four boxes and a
   live sample, and the sample is the real function: a rule of hyphens is not
   something anybody can picture from "width 96".

   The reader still has to be able to read it back - that is what keeps a
   cleanup idempotent - so the shape is fixed and only its furniture moves. */
function eduTidyStyleBox(){
  const s=eduTidy.style;
  const fills=['-','=','*','~','#','_','+','.'];
  return `<fieldset><legend>${tt('edusort.section_banners')}</legend>
    <div class="brow eduband">
      <label>${tt('edusort.width')}<input type="number" min="20" max="200" value="${esc(s.width)}"
        oninput="eduTidyStyle('width',this.value)"></label>
      <label>${tt('edusort.line_character')}<select onchange="eduTidyStyle('fill',this.value)">
        ${fills.map(f=>`<option value="${esc(f)}"${f===s.fill?' selected':''}>${esc(f)}</option>`).join('')}
      </select></label>
      <label>${tt('edusort.starts_with')}<input value="${esc(s.prefix)}" maxlength="6"
        title="${ttA('edusort.a_comment_in_this_file_starts')}"
        oninput="eduTidyStyle('prefix',this.value)"></label>
      <label class="chk"><input type="checkbox" ${s.upper?'checked':''}
        onchange="eduTidyStyle('upper',this.checked)"> ${tt('edusort.capitals')}</label>
    </div>
    <div class="edusample"><code>${esc(eduTidySample())}</code></div>
    <div class="count">${docPoints(tt('edusort.this_is_the_only_line_the'),[
      tt('edusort.everything_else_in_the_file_is'),
      tt('edusort.the_shape_is_fixed_so_the_next')])}</div>
  </fieldset>`;
}
/* The sample, worked out in the page.

   It has to be the SAME arithmetic as edusort.banner, to the character: a sample
   that is not what gets written is worse than no sample, because it is the only
   thing anyone will check the setting against. The line is exactly `width`
   characters long, prefix and the two spaces around the title included. */
function eduTidySample(){
  const s=eduTidy.style;
  const title=s.upper?tt('edusort.gondor_tier_2_infantry'):tt('edusort.gondor_tier_2_infantry_2');
  const width=Math.max(20,Math.min(200,parseInt(s.width,10)||95));
  const pad=Math.max(4,width-title.length-(s.prefix||';').length-2);
  const left=Math.floor(pad/2);
  return (s.prefix||';')+(s.fill||'-').repeat(left)+' '+title+' '
    +(s.fill||'-').repeat(pad-left);
}
function eduTidyStyle(k,v){
  eduTidy.style[k]=(k==='upper')?!!v:v;
  // the sample redraws at once; the plan behind it is worth a moment's wait
  const el=document.querySelector('#eduBody .edusample code');
  if(el)el.textContent=eduTidySample();
  eduTidyPlanSoon();
}
let _eduPlanT=null;
function eduTidyPlanSoon(){clearTimeout(_eduPlanT); _eduPlanT=setTimeout(eduTidyPlan,400);}

function eduTidyClean(){
  const p=eduTidy.plan;
  const opts=`<fieldset><legend>${tt('edusort.what_to_do')}</legend>
    ${eduOpt('group',tt('edusort.group_the_units_into_sections'),
             tt('edusort.move_each_unit_into_its_factions'))}
    ${eduOpt('tiers',tt('edusort.read_tiers_from_the_files_own'),
             tt('edusort.a_banner_like_gondor_tier_2'))}
    ${eduOpt('banners',tt('edusort.write_a_banner_above_each_section'),
             tt('edusort.one_comment_line_naming_the_section'))}
    ${eduOpt('tidy',tt('edusort.line_every_units_values_up_in'),
             tt('edusort.rewrites_only_the_gap_between_a'))}
    <div class="count" style="margin-top:6px">${docPoints(
      tt('edusort.this_rewrites_the_whole_unit_file'),[
      tt('edusort.it_only_ever_moves_a_block_no'),
      tt('edusort.a_tier_read_from_a_banner_is'),
      tt('edusort.one_backup_one_entry_in_the')])}</div>
  </fieldset>`
  +(eduTidy.opts.banners?eduTidyStyleBox():'');
  if(!p)return opts+`<div class="empty">${tt('common.working_out_what_would_change')}</div>`;
  if(p.errors.length)
    return opts+`<div class="w-bad">${p.errors.map(esc).join('<br>')}</div>`;
  if(!p.touched)
    return opts+`<div class="empty">${tt('edusort.this_file_is_already_in_shape')}</div>`;
  const secs=p.sections.map(s=>`<tr><td>${esc(s.name)}</td>
    <td class="num">${s.units}</td></tr>`).join('');
  return opts+`
    <div class="cards"><ul>${p.changes.map(c=>`<li>${esc(c)}</li>`).join('')}</ul></div>
    ${p.warnings.length?`<div class="w-warn">${p.warnings.map(esc).join('<br>')}</div>`:''}
    <div class="two">
      <div><h3>${tt('edusort.sections',{sections_n:p.sections.length})}</h3>
        <div class="scroll" style="max-height:280px"><table class="grid">
          <thead><tr><th>${tt('edusort.section')}</th><th class="num">${tt('edusort.units')}</th></tr></thead>
          <tbody>${secs}</tbody></table></div></div>
      <div><h3>${tt('edusort.units_that_move',{moved_count:p.moved_count})}</h3>
        <div class="scroll count" style="max-height:280px">${
          p.moved.map(esc).join('<br>')||tt('common.none_3')}${
          p.moved_count>p.moved.length?`<br><span class="count">${tt('edusort.and_more',{n:p.moved_count-p.moved.length})}</span>`:''}</div></div>
    </div>`;
}

/* ---- the per-section order screen ----------------------------------------
   This was a row of draggable chips, and dragging was the only thing it could
   do. But the reason a unit is in the wrong place is almost never "the sorter
   guessed badly at an order" - it is that the unit has no tier, or the wrong
   one, or is a bodyguard nothing marked as one. Dragging it papers over that
   for one run; setting the tier fixes it for every run, and for every other
   screen in the toolkit that reads the same marker.

   So each unit is a ROW now, with the three things the sorter reads beside it:
   tier, variant and classification. The classification arrives filled in with
   whatever the unit's own `attributes` say, so agreeing with the tool is free.
   Dragging still works, and is still what a hand placement is.
   ========================================================================= */
function eduTidyOrder(){
  const t=eduTidy;
  if(!t.sections.length)return `<div class="empty">${tt('edusort.reading_the_unit_file')}</div>`;
  const q=(t.q||'').toLowerCase();
  const shown=t.sections.map(s=>({name:s.name,
      units:s.units.filter(u=>!q||u.type.toLowerCase().includes(q)
        ||(u.name||'').toLowerCase().includes(q))}))
    .filter(s=>s.units.length);
  return `<div class="count">${docPoints(
      tt('edusort.set_what_the_sorter_reads_and'),[
      tt('edusort.a_unit_with_no_tier_sorts_after'),
      tt('edusort.classification_is_what_makes_a_unit_lead'),
      tt('edusort.drag_a_unit_onto_another_to'),
      tt('edusort.none_of_it_is_written_until')])}</div>
    <div class="basebar" style="margin:8px 0">
      <input id="eduQ" placeholder="${ttA('edusort.filter_these_units')}" value="${esc(t.q)}"
        oninput="eduTidyFind(this.value)">
      ${tt('edusort.unit_s_shown',{x:eduTidyMarkCount()?`<button onclick="eduTidyClearMarks()">${tt('edusort.undo_my_edit_s',{eduTidyMarkCount:eduTidyMarkCount()})}</button>`:'',x2:shown.reduce((n,s)=>n+s.units.length,0)})}
    </div>
    ${shown.map(s=>`<fieldset style="margin-top:10px">
      <legend>${esc(s.name)} <span class="count">${s.units.length}</span></legend>
      <div class="edulist">
        <div class="edurow eduhd">${tt('edusort.unit_tier_variant_classification_kind')}</div>
        ${s.units.map(u=>eduTidyRow(s.name,u)).join('')}
      </div></fieldset>`).join('')||`<div class="empty">${tt('edusort.no_unit_matches_that')}</div>`}`;
}
// What a unit shows right now: the pending edit, then the file's own marker.
function eduTidyMark(type,key){
  const m=eduTidy.marks[type];
  return (m&&m[key]!==undefined)?m[key]:null;
}
function eduTidyVal(u,key){
  const m=eduTidyMark(u.type,key);
  if(m!==null)return m;
  // The classification falls back to what was DETECTED, so the drop-down shows
  // the answer the sorter is already using rather than an empty box that looks
  // like nothing has been decided.
  if(key==='special')return u.special||u.detected_special||'';
  return u[key]||'';
}
const eduTidyEdited=(type,key)=>eduTidyMark(type,key)!==null;
function eduTidyMarkCount(){return Object.keys(eduTidy.marks).length;}
/* A drop-down changed. Only that ROW is redrawn.

   The list is the whole roster - 916 units on Divide and Conquer, each with
   three drop-downs - and rebuilding it takes most of a second. Doing that on
   every pick made the list feel broken: the box you had just used was replaced
   under the pointer, and picking three values in a row meant waiting three
   times. Nothing outside the row changes except the count in the footer, so
   nothing outside the row is touched. */
function eduTidySetMark(type,key,value){
  const t=eduTidy;
  const u=t.sections.flatMap(s=>s.units).find(x=>x.type===type); if(!u)return;
  const was=key==='special'?(u.special||u.detected_special||''):(u[key]||'');
  const m=t.marks[type]||{};
  if(value===was)delete m[key]; else m[key]=value;
  if(Object.keys(m).length)t.marks[type]=m; else delete t.marks[type];
  // the unit's own copy follows, so the row redraws with what was picked
  u[key==='special'?'special':key]=value;
  const row=document.querySelector(`#eduBody .edurow[data-type="${cssq(type)}"]`);
  if(row){
    const sec=row.dataset.sec;
    row.outerHTML=eduTidyRow(sec,u);
    eduTidyWireOrder();
  }else{
    renderEduTidy();
  }
  eduTidyPaintFoot();
  eduTidyPlanSoon();
}
// The footer's running count, without redrawing the list behind it.
function eduTidyPaintFoot(){
  const el=document.querySelector('#modal .foot .count');
  if(el)el.textContent=eduTidyMarkCount()
    ?tt('edusort.unit_s_edited_on_the_order',{eduTidyMarkCount:eduTidyMarkCount()}):'';
}
function eduTidyClearMarks(){
  eduTidy.marks={}; eduTidy.sections=[];
  renderEduTidy(); eduTidyLoadOrder(); eduTidyPlanSoon();
}
function eduTidyFind(v){
  eduTidy.q=v;
  const body=document.getElementById('eduBody');
  if(body){body.innerHTML=eduTidyOrder(); eduTidyWireOrder();
    const el=document.getElementById('eduQ');
    if(el){el.focus(); el.setSelectionRange(el.value.length,el.value.length);}}
}
// One drop-down, with whatever the unit already has kept in the list even when
// the mod's own vocabulary does not have it.
function eduTidySel(u,key,list,blank){
  const cur=eduTidyVal(u,key);
  const all=(list||[]).slice();
  if(cur&&all.indexOf(cur)<0)all.push(cur);
  return `<select class="mini${eduTidyEdited(u.type,key)?' edited':''}"
    onchange="eduTidySetMark('${q1(esc(u.type))}','${key}',this.value)">
    <option value="">${esc(blank)}</option>
    ${all.map(v=>`<option value="${esc(v)}"${v===cur?' selected':''}>${esc(v)}</option>`).join('')}
  </select>`;
}
function eduTidyRow(section,u){
  const t=eduTidy,v=t.vocab;
  const hand=(t.hand[section]||[]).indexOf(u.type)>=0;
  const special=eduTidyVal(u,'special');
  // "detected" says the value in the box is the tool's reading rather than
  // anyone's decision - the difference matters when you are deciding whether to
  // trust it.
  const from=(!u.special&&u.detected_special&&special===u.detected_special)
    ? `<span class="count">${tt('edusort.detected')}</span>` : '';
  return `<div class="edurow${hand?' placed':''}" draggable="true"
      data-sec="${esc(section)}" data-type="${esc(u.type)}">
    <span class="euu" title="${esc(u.type)}">
      <span class="g" title="${ttA('edusort.drag_to_place_this_unit_by')}">⠿</span>
      <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,u.type)}" alt="">
      <span class="eunm"><span class="nm">${esc(u.name||u.type)}</span>
        <span class="ty">${esc(u.type)}${hand?tt('edusort.placed_by_hand'):''}</span></span></span>
    <span class="eun">${eduTidySel(u,'tier',v.tiers,tt('edusort.no_tier'))}</span>
    <span class="eun">${eduTidySel(u,'variant',v.variants,tt('common.none_2'))}</span>
    <span class="eun">${eduTidySel(u,'special',v.specials,tt('edusort.ordinary_unit'))}${from}</span>
    <span class="euk count">${esc(u.category||'')}</span></div>`;
}

function eduTidyWireOrder(){
  let from=null;
  document.querySelectorAll('#eduBody .edurow[data-type]').forEach(el=>{
    el.ondragstart=ev=>{
      // a drag that starts inside a drop-down is the drop-down's, not the row's
      if(ev.target.closest('select,input')){ev.preventDefault(); return;}
      from={sec:el.dataset.sec,type:el.dataset.type};
      ev.dataTransfer.effectAllowed='move'; el.classList.add('drag');};
    el.ondragover=ev=>{if(from&&from.sec===el.dataset.sec){ev.preventDefault();
      el.classList.add('over');}};
    el.ondragleave=()=>el.classList.remove('over');
    el.ondragend=()=>{el.classList.remove('drag'); from=null;};
    el.ondrop=ev=>{
      if(!from||from.sec!==el.dataset.sec)return;
      ev.preventDefault();
      const s=eduTidy.sections.find(x=>x.name===el.dataset.sec);
      const i=s.units.findIndex(u=>u.type===from.type);
      const to=s.units.findIndex(u=>u.type===el.dataset.type);
      if(i<0||to<0||i===to){from=null; return;}
      const [moved]=s.units.splice(i,1); s.units.splice(to,0,moved);
      eduTidy.hand[s.name]=s.units.map(u=>u.type);
      from=null; renderEduTidy(); eduTidyPlan();
    };
  });
}

async function eduTidyLoadOrder(){
  try{
    const r=await api.get(`/api/edu/order?mod=${enc(eduTidy.mod)}`);
    eduTidy.sections=r.sections||[];
    eduTidy.vocab={tiers:r.tiers||[],variants:r.variants||[],specials:r.specials||[]};
    if(r.banner_style)eduTidy.style=Object.assign({},eduTidy.style,r.banner_style);
  }catch(e){ toast(''+e,4000); }
  renderEduTidy();
}

async function eduTidyPlan(){
  const t=eduTidy;
  try{
    const r=await api.post('/api/edu/sort/plan',
      Object.assign({mod:t.mod,hand:t.hand,marks:t.marks,style:t.style},t.opts));
    t.plan=r.plan||{errors:[r.error||tt('edusort.no_answer')],changes:[],warnings:[],
                    sections:[],moved:[],moved_count:0,touched:false};
  }catch(e){
    t.plan={errors:[''+e],changes:[],warnings:[],sections:[],moved:[],
            moved_count:0,touched:false};
  }
  renderEduTidy();
}

async function eduTidyApply(){
  const t=eduTidy;
  t.busy=true; renderEduTidy();
  try{
    const r=await api.post('/api/edu/sort/apply',
      Object.assign({mod:t.mod,hand:t.hand,marks:t.marks,style:t.style},t.opts));
    if(r.error){toast(r.error,5000); return;}
    activity(tt('edusort.cleaned_up_the_unit_file'),
             tt('edusort.unit_s_moved_in',{moved:r.moved,mod:t.mod}));
    toast(tt('edusort.unit_file_cleaned_up_unit_s',{moved:r.moved}),5000);
    closeModal();
    loadSource();                // the roster on screen came from the file we just rewrote
  }catch(e){ toast(''+e,5000); }
  finally{ t.busy=false; }
}
