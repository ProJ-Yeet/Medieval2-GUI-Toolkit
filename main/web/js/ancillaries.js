/* ancillaries.js - Ancillaries mode: export_descr_ancillaries.txt, both halves

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= ANCILLARIES MODE =======================
   The retinue: the items and followers a character picks up. EDA is EDCT's
   smaller sibling - same file shape, same trigger language below - so this
   screen is the traits screen with the level ladder taken out and a picture put
   in. What differs is worth knowing:

     * `Type` groups ancillaries: a character holds one per type, so it is the
       field that decides what a new one replaces. Free-form, so the picker
       offers the ones this mod already uses rather than a fixed list.
     * `Transferable` is whether it can be handed to another character.
     * Two limits are silent and hardcoded: more than 3 ExcludedAncillaries is an
       errorless crash, more than 8 effects makes the ancillary impossible to
       gain from a trigger. Both are checked before a save, not after.
     * Its name is its own text key - unlike a trait, which borrows its first
       level's - so the box beside the name IS what the player reads.

   THE PAGE NEVER PARSES A GAME FILE: /api/ancillaries, /api/ancillary and
   /api/ancillaries/plan|apply do all of it, and a save posts back the shape the
   server's own render_block takes. */

const AN_BLANK = {name:'', type:'item', transferable:'1', image:'', unique:false,
  excluded_ancillaries:[], exclude_cultures:[], description:'',
  effects_description:'', effects:[]};

async function loadAncillaries(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ` + esc(mod) + `${tt('ancillaries.s_ancillaries')}</div>`;
  let r;
  try{ r = await api.get('/api/ancillaries?mod=' + enc(mod)); }
  catch(e){ if(stale('ancillaries', mod)) return;
    main.innerHTML = `<div class="empty">${tt('ancillaries.couldnt_read_the_ancillaries_file')}<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadAncillaries()">${tt('common.retry')}</button></div>`; return; }
  if(stale('ancillaries', mod)) return;
  state.an = Object.assign({sel:'', d:null, busy:false, adding:false}, r);
  undoReset();
  renderAncillaries();
}

function renderAncillaries(){
  const a = state.an;
  if(!a){ loadAncillaries(); return; }
  const strip = minorTabsHtml('', 'data/export_descr_ancillaries.txt');
  if(a.error || !a.exists){
    main.innerHTML = strip + `<div class="empty">${tt('ancillaries.they_live_in_data_export_descr',{error:esc(a.error || tt('ancillaries.no_ancillaries_file'))})}</div>`;
    return;
  }
  const rows = anRows();
  count.textContent = `${rows.length}/${a.count}`;
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      <button class="trnew" onclick="anNew()">${tt('ancillaries.new_ancillary')}</button>
      <button class="trnew" onclick="portOpen('ancillaries')" title="${ttA('ancillaries.copy_ancillaries_out_of_another_mod')}">${tt('ancillaries.port_from_another_mod')}</button>
      ${findingsHtml('ancillaries', a.finding_list, 'anOpen')}
      <div class="trrows">${rows.map(anRowHtml).join('')
        || `<div class="count" style="padding:8px">${tt('ancillaries.no_ancillary_matches')}</div>`}</div>
    </div>
    <div class="trmain" id="anMain">${anDetailHtml()}</div>
  </div>`;
}

// Filtered in the page: 700 rows is a list, and the file was parsed once to
// build it anyway. The type is searchable too - it is how a modder groups them.
function anRows(){
  const q = search.value.trim().toLowerCase();
  const rows = state.an.ancillaries || [];
  if(!q) return rows;
  return rows.filter(r => r.name.toLowerCase().includes(q)
    || (r.label||'').toLowerCase().includes(q)
    || (r.type||'').toLowerCase().includes(q));
}

function anRowHtml(r){
  const on = state.an.sel === r.name;
  return `<button class="trrow anrow${on?' on':''}" onclick="anOpen('${q1(esc(r.name))}')">
    <img class="anpic" src="${anImgUrl(r.image)}" alt="" loading="lazy"
      onerror="iconRetry(this)">
    <span class="antxt">
      <span class="nm">${esc(r.label)}</span>
      <span class="sub">${esc(r.type||tt('ancillaries.no_type'))}${r.unique?tt('ancillaries.unique'):''}${
        r.effects?tt('ancillaries.effect',{effects:r.effects,effects2:r.effects===1?'':'s'}):''}${
        r.triggers?tt('ancillaries.trigger',{triggers:r.triggers,triggers2:r.triggers===1?'':'s'})
                  :r.lua_gives?tt('ancillaries.given_by_a_script')
                  :` ${tt('ancillaries.nothing_grants_it',{lua_names:r.lua_names?tt('ancillaries.a_script_names_it'):''})}`}${
        r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''}</span>
    </span>
  </button>`;
}

const anImgUrl = image => `/icon?mod=${enc(state.an.mod)}&kind=ancillary`
  + `&image=${enc(image||'')}` + iconBust();

async function anOpen(name){
  activity(tt('ancillaries.opened_ancillary'), `${name} in ${state.src}`);
  const a = state.an;
  a.sel = name; a.adding = false; a.d = null;
  renderAncillaries();
  let d;
  try{ d = await api.get(`/api/ancillary?mod=${enc(a.mod)}&name=${enc(name)}`); }
  catch(e){ d = {error:''+e}; }
  if(state.mode !== 'ancillaries' || state.an !== a || a.sel !== name) return;
  a.d = d.error ? d : anWorking(d);
  undoReset();          // the working copy exists now: this is Ctrl+Z's baseline
  anPaint();
  if(!d.error && state.settings.code_view) anCvToggle();
}

function anWorking(d){
  d.w = JSON.parse(JSON.stringify(d.ancillary));
  d.trigs = (d.triggers || []).map(t => ({name:t.name, ui:null, dirty:false, src:t}));
  d.locEdits = {};
  return d;
}

function anNew(){
  const a = state.an;
  a.sel = ''; a.adding = true;
  a.d = {name:'', label:tt('ancillaries.new_ancillary_2'),
    ancillary:JSON.parse(JSON.stringify(AN_BLANK)),
    w:JSON.parse(JSON.stringify(AN_BLANK)),
    trigs:[], findings:[], loc:{}, locEdits:{}, missing_loc:[], triggers:[],
    known:(a.ancillaries||[]).map(r=>r.name), types:a.types||[],
    attributes:a.attributes||[]};
  renderAncillaries();
}

function anPaint(){
  const el = document.getElementById('anMain');
  if(el) el.innerHTML = anDetailHtml();
  const d = state.an.d;
  if(d && d.cv){ cvWire(d.cv); cvBindHover(d.cv, document.getElementById('anGui')); }
  anWireTriggers();
}

// The form only - never the pane, which has the caret in it.
function anPaintForm(){
  const d = state.an.d, el = document.getElementById('anGui');
  if(!d || !el) return;
  el.innerHTML = anFindingsHtml(d) + anFormHtml(d.w, d);
  if(d.cv) cvBindHover(d.cv, el);
}

/* ---- the detail pane ---- */
function anDetailHtml(){
  const a = state.an, d = a.d;
  if(!a.sel && !a.adding) return `<div class="empty">${tt('ancillaries.pick_an_ancillary_on_the_left',{count:a.count,count2:a.count===1?'y':'ies',triggers:a.triggers,triggers2:a.triggers===1?'':'s',file:esc(a.file)})}</div>`;
  if(!d) return `<div class="empty">${tt('ancillaries.reading_the_ancillary')}</div>`;
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  return `<div class="trbar">
      <div><b>${esc(a.adding ? tt('ancillaries.new_ancillary_3') : d.label)}</b>
        <span class="count">${esc(d.w.type || tt('ancillaries.no_type'))}</span></div>
      <span class="sp"></span>
      ${a.adding ? '' : `<button class="${d.cv?'on':''}" title="${ttA('ancillaries.show_this_ancillary_exactly_as_export')}"
        onclick="anCvToggle()">${tt('common.code_view')}</button>
      <button class="danger" onclick="anDelete()">${tt('common.delete')}</button>`}
      <button class="primary" onclick="anSave()">${a.adding?tt('common.create'):tt('common.save')}</button>
    </div>
    <div id="anGui">
      ${anFindingsHtml(d)}
      ${anFormHtml(d.w, d)}
    </div>
    ${d.cv ? `<div id="anCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : ''}
    ${anTriggersHtml(d)}`;
}

function anFindingsHtml(d){
  const out = (d.findings||[]).map(f =>
    `<div class="trfind w-warn">${tt('ancillaries.line',{line:f.line,message:esc(f.message)})}</div>`);
  if((d.missing_loc||[]).length) out.push(`<div class="trfind w-warn">${tt('ancillaries.text_key_s_are_not_in',{missing_loc_n:d.missing_loc.length,missing_loc:d.missing_loc.map(esc).join(', ')})}</div>`);
  return out.join('');
}

function anFormHtml(w, d){
  /* The key on the left, the words the player reads on the right - and the words
     box is bound to the FIELD, not to the key that field holds right now. Bound
     to the key, the handler baked in whatever the box held when the form was
     last drawn, and typing a key does not redraw the form: the words went in
     under the old (usually empty) tag, never reached the save, and the ancillary
     was written with its own code name as its text. The box is always drawn for
     the same reason - a key typed into an empty box would otherwise have nowhere
     to put its words until something else redrew. */
  const key = (k, label, hint) => {
    const tag = (w[k] || '').trim();
    return `<label class="lbl" data-label="${k}">${label}</label>
      <div class="trkey">
        <input data-label="${k}" value="${esc(w[k]||'')}" placeholder="${esc(hint||'')}"
          oninput="anSet('${k}',this.value.trim())">
        <input class="trtext" value="${esc(anLocTextAt(d, k))}"
          placeholder="${tag ? (anHasKey(d, tag)?'':tt('ancillaries.not_in_export_ancillaries_txt_yet'))
                             : tt('ancillaries.name_the_key_on_the_left')}"
          title="${ttA('ancillaries.what_the_player_reads_saved_into')}"
          oninput="anSetLocAt('${k}',this.value)">
      </div>`;
  };
  return `<section class="trsec">
    <div class="trsechead">${tt('ancillaries.the_ancillary_the_order_of_these')}</div>
    <div class="anhead">
      <div class="anpicbox">
        <div class="icowrap">
          <img class="anbig" src="${anImgUrl(w.image)}" alt="" onerror="iconRetry(this)"
            title="${ttA('common.replace_this_picture')}"
            onclick="imgPick('${q1(esc(anImgUrl(w.image)))}','anPaint')">
          ${imgEditBtn(anImgUrl(w.image),'anPaint')}
        </div>
        ${imgWhereBtn(anImgUrl(w.image),tt('ancillaries.where_is_it'))}
      </div>
      <div class="trgrid" style="flex:1">
        <label class="lbl" data-label="name">${tt('common.name')}</label>
        <div class="trkey">
          <input data-label="name" value="${esc(w.name)}"
            ${state.an.adding?'':'disabled'} placeholder="ancillary_name"
            oninput="anSet('name',this.value.trim())">
          <input class="trtext" value="${esc(anLocTextAt(d, 'name'))}"
            placeholder="${w.name ? (anHasKey(d, w.name)?'':tt('ancillaries.the_name_on_the_character_screen'))
                                  : tt('ancillaries.name_the_ancillary_first')}"
            title="${ttA('ancillaries.the_ancillarys_name_as_the_player')}"
            oninput="anSetLocAt('name',this.value)">
        </div>
        <label class="lbl" data-label="type">${tt('common.type')}</label>
        <div>
          <input data-label="type" value="${esc(w.type)}" list="anTypes"
            placeholder="${ttA('ancillaries.item')}" oninput="anSet('type',this.value.trim())">
          <datalist id="anTypes">${(d.types||[]).map(t =>
            `<option value="${esc(t)}">`).join('')}</datalist>
          <div class="trhint count">${tt('ancillaries.a_character_holds_one_ancillary_per')}</div>
        </div>
        <label class="lbl" data-label="image">${tt('ancillaries.image')}</label>
        <div>
          <input data-label="image" value="${esc(w.image)}" placeholder="name.tga"
            oninput="anSet('image',this.value.trim())">
          ${d.image_found === false ? `<div class="trhint w-warn">${tt('ancillaries.not_found_in_data_ui_ancillaries')}</div>` : ''}
        </div>
        <label class="lbl" data-label="transferable">${tt('ancillaries.transferable')}</label>
        <div data-label="transferable"><label class="chk"><input type="checkbox"
          ${w.transferable !== '0' ? 'checked' : ''}
          onchange="anSet('transferable',this.checked?'1':'0')">
          ${tt('ancillaries.can_be_handed_to_another_character')}</label></div>
        <label class="lbl" data-label="unique">${tt('ancillaries.unique_2')}</label>
        <div data-label="unique"><label class="chk"><input type="checkbox"
          ${w.unique?'checked':''} onchange="anSet('unique',this.checked)">
          ${tt('ancillaries.can_only_ever_be_acquired_once')}</label></div>
      </div>
    </div>
    <div class="trgrid" style="margin-top:8px">
      <label class="lbl" data-label="excluded_ancillaries">${tt('ancillaries.excludedancillaries')}</label>
      <div>
        <input data-label="excluded_ancillaries"
          value="${esc((w.excluded_ancillaries||[]).join(', '))}" list="anNames"
          placeholder="${ttA('common.none')}"
          oninput="anSet('excluded_ancillaries',this.value.split(',').map(s=>s.trim()).filter(Boolean))">
        <datalist id="anNames">${(d.known||[]).map(n =>
          `<option value="${esc(n)}">`).join('')}</datalist>
        ${(w.excluded_ancillaries||[]).length > 3
          ? `<div class="trhint w-bad">${tt('ancillaries.more_than_3_is_an_errorless')}</div>`
          : (w.unique && !(w.excluded_ancillaries||[]).includes(w.name)
             ? `<div class="trhint w-warn">${tt('ancillaries.a_unique_ancillary_needs_its_own')}</div>` : '')}
      </div>
      <label class="lbl" data-label="exclude_cultures">${tt('ancillaries.excludecultures')}</label>
      <input data-label="exclude_cultures"
        value="${esc((w.exclude_cultures||[]).join(', '))}" placeholder="${ttA('common.none')}"
        oninput="anSet('exclude_cultures',this.value.split(',').map(s=>s.trim()).filter(Boolean))">
      ${key('description',tt('common.description'), w.name?w.name+'_desc':'')}
      ${key('effects_description','EffectsDescription',
            w.name?w.name+'_effects_desc':'')}
    </div>
    <div class="treffects">
      <div class="trsechead" style="margin:8px 0 0">${tt('ancillaries.effects_8_more_than_8_makes',{n:(w.effects||[]).length})}</div>
      ${(w.effects||[]).map((e,k)=>anEffectHtml(e,k,d)).join('')}
      ${(w.effects||[]).length < 8
        ? `<button class="trgadd" onclick="anAddEffect()">${tt('ancillaries.add_effect')}</button>` : ''}
    </div>
  </section>`;
}

function anEffectHtml(e, k, d){
  const attrs = d.attributes || [];
  const known = !e.attribute || attrs.includes(e.attribute)
    || /^Combat_V_(Faction|Religion)_./.test(e.attribute);
  return `<div class="treff" data-label="effect#${k+1}">
    <input class="trattr${known?'':' bad'}" value="${esc(e.attribute)}" list="anAttrs"
      placeholder="${ttA('ancillaries.attribute')}" oninput="anSetEffect(${k},'attribute',this.value.trim())">
    <input class="trnum" value="${esc(e.amount)}"
      oninput="anSetEffect(${k},'amount',this.value.trim())">
    ${known?'':`<span class="count w-warn">${tt('ancillaries.not_a_character_attribute')}</span>`}
    <button class="trgdel" onclick="anDelEffect(${k})">✕</button>
    <datalist id="anAttrs">${attrs.map(x=>`<option value="${esc(x)}">`).join('')}</datalist>
  </div>`;
}

/* ---- the triggers that grant it ----
   `AcquireAncillary` is EDA's `Affects`, and the builder is the same one the
   traits editor hosts (web/js/triggerui.js). */
function anTriggersHtml(d){
  if(state.an.adding) return `<section class="trsec">
    <div class="trsechead">${tt('common.triggers')}</div>
    <div class="count" style="padding:6px">${tt('ancillaries.create_the_ancillary_first_a_trigger')}</div></section>`;
  return `<section class="trsec">
    <div class="trsechead">${tt('common.triggers')} <span class="count">${d.trigs.length
      ? tt('ancillaries.what_grants_this_ancillary')
      : luaGives(d.lua) ? tt('ancillaries.no_trigger_a_script_grants_it')
      : tt('ancillaries.nothing_grants_this_ancillary')}</span></div>
    ${luaHitsHtml(d.lua, 'ancillary')}
    ${d.trigs.map((t,i)=>`<div class="trtrig">
      <div class="trtrighead"><b>${esc(t.name)}</b><span class="sp"></span>
        <button class="trgdel" title="${ttA('common.remove_this_trigger')}"
          onclick="anDelTrigger(${i})">✕</button></div>
      <div id="antrg-${i}"></div>
    </div>`).join('')}
    <button class="trgadd" onclick="anAddTrigger()">${tt('common.add_trigger')}</button>
  </section>`;
}

async function anWireTriggers(){
  const d = state.an.d;
  if(!d || !d.trigs) return;
  for(let i = 0; i < d.trigs.length; i++){
    if(!document.getElementById('antrg-' + i)) continue;
    const row = d.trigs[i];
    if(!row.ui){
      row.ui = trgCreate({mod:state.an.mod, trigger:row.src,
        onChange:() => { row.dirty = true; }});
      await trgLoad(row.ui);
    }
    const here = document.getElementById('antrg-' + i);
    if(here) here.innerHTML = trgHtml(row.ui);
  }
}

/* ---- edits ---- */
function anSet(key, value){
  const d = state.an.d; if(!d) return;
  d.w[key] = value;
  // these change the shape of the form (a warning appears, a picture changes)
  anRepaintIf(['unique','image','excluded_ancillaries','transferable','type']
    .includes(key));
}
function anSetEffect(k, key, value){
  const e = state.an.d.w.effects[k]; if(!e) return;
  e[key] = value;
  anRepaintIf(false);
}
function anAddEffect(){
  const w = state.an.d.w;
  (w.effects = w.effects || []).push({attribute:'', amount:'1'});
  anRepaintIf(true);
}
function anDelEffect(k){
  state.an.d.w.effects.splice(k, 1);
  anRepaintIf(true);
}
/* `locEdits` is keyed by the FIELD typed into (`name`, `description`,
   `effects_description`), not by the key that field held when the form was
   drawn. The tags are resolved once, at save time, in `anLocBody` - which is
   also what carries typed words across a rename of the key they belong to. */
const anHasKey = (d, tag) => tag && (d.loc||{})[tag] !== undefined;
const anTagAt = (d, field) => String((d && d.w && d.w[field]) || '').trim();
function anLocTextAt(d, field){
  const tag = anTagAt(d, field);
  if(!tag) return '';
  const e = (d.locEdits || {})[field];
  return e !== undefined ? e : ((d.loc||{})[tag] || '');
}
function anSetLocAt(field, value){
  const d = state.an.d; if(!d) return;
  (d.locEdits = d.locEdits || {})[field] = value;
  if(d.cv) cvFromGui(d.cv);
}
// field -> the key that field names now. An emptied key writes nothing.
function anLocBody(){
  const d = state.an.d, out = {};
  for(const [field, value] of Object.entries((d && d.locEdits) || {})){
    const tag = anTagAt(d, field);
    if(tag) out[tag] = value;
  }
  return out;
}
// The GUI→pane half of the Code View contract: change a box and the text pane
// is re-serialised by the server, through the serialiser the save itself uses.
function anRepaintIf(yes){
  const d = state.an.d; if(!d) return;
  if(yes) anPaintForm();
  if(d.cv) cvFromGui(d.cv);
}

function anAddTrigger(){
  const d = state.an.d; if(!d) return;
  const n = (d.name || 'anc').toLowerCase() + '_' + (d.trigs.length + 1);
  d.trigs.push({name:n, ui:null, dirty:true, added:true,
    src:{name:n, when_to_test:'CharacterTurnEnd', conditions:[],
         effects:[{keyword:'AcquireAncillary', args:[d.name, 'chance', '5']}]}});
  anPaint();
}
function anDelTrigger(i){
  const d = state.an.d, row = d.trigs[i];
  if(!row.added && !confirm(tt('ancillaries.remove_trigger',{name:row.name})
    + tt('common.it_is_written_out_of_the'))) return;
  if(row.ui) trgDrop(row.ui);
  d.trigs.splice(i, 1);
  d.removed = (d.removed || []).concat(row.added ? [] : [row.name]);
  anPaint();
}

/* ---- the code view ---- */
async function anCvToggle(){
  const d = state.an.d; if(!d) return;
  if(d.cv){ cvDrop(d.cv); d.cv = null; state.settings.code_view = false;
    api.post('/api/settings', {code_view:false}); anPaint(); return; }
  state.settings.code_view = true; api.post('/api/settings', {code_view:true});
  d.cv = cvCreate({kind:'ancillaries', mod:state.an.mod, id:d.name,
    where:'data/' + state.an.file,
    edits:() => anEdits(),
    adopt:cv => { const s = state.an.d;
      if(!cv.detail) return;
      s.w = cv.detail;
      // `base`, never `text`: with comment hiding on, `text` is the view with the
      // comment-only lines cut out of it, and saving that would delete every one
      // of them. `base` is the record's real bytes.
      s.raw = cv.edited ? cv.base : ''; },
    refreshGui:() => anPaintForm()});
  anPaint();
  await cvLoad(d.cv);
  if(state.an.d !== d || !d.cv) return;
  anPaint();
}

/* ---- writing ---- */
function anEdits(){
  const w = state.an.d.w;
  return {name:w.name, type:w.type, transferable:w.transferable, image:w.image,
    unique:w.unique, excluded_ancillaries:w.excluded_ancillaries,
    exclude_cultures:w.exclude_cultures, description:w.description,
    effects_description:w.effects_description,
    effects:(w.effects||[]).filter(e => e.attribute && e.amount)};
}

function anBody(action){
  const a = state.an, d = a.d;
  const body = {mod:a.mod, ancillary:action === 'add' ? d.w.name : d.name, action};
  if(action !== 'delete'){
    body.edits = anEdits();
    body.loc = anLocBody();
    if(d.raw) body.raw_block = d.raw;
    const adds = [], edits = [];
    for(const row of (d.trigs || [])){
      if(!row.ui || !row.dirty) continue;
      (row.added ? adds : edits).push({name:row.name, trigger:trgValue(row.ui)});
    }
    body.triggers = {adds, edits, removes:d.removed || []};
  }
  return body;
}

async function anSave(){
  const a = state.an, d = a.d;
  if(a.adding && !d.w.name.trim()){ toast(tt('ancillaries.a_new_ancillary_needs_a_name'), 3500); return; }
  await anApply(anBody(a.adding ? 'add' : 'edit'),
                a.adding ? `create ${d.w.name}` : `save ${d.name}`);
}
async function anDelete(){
  await anApply(anBody('delete'), `delete ${state.an.d.name}`);
}

async function anApply(body, what){
  const a = state.an;
  if(a.busy) return;
  a.busy = true;
  let plan;
  try{ plan = await api.post('/api/ancillaries/plan', body); }
  finally{ a.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 6000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 14);
  const found = (p.findings || []).map(f => '⚠ ' + f.message);
  if(!confirm(tt('ancillaries.write',{what}) + (lines.join('\n') || tt('common.no_visible_change'))
    + ((p.changes || []).length > 14 ? tt('ancillaries.and_more',{changes:p.changes.length - 14}) : '')
    + (found.length ? '\n\n' + found.slice(0, 4).join('\n') : '')
    + tt('common.backed_up_first_and_log_can'))) return;
  a.busy = true;
  let res;
  try{ res = await api.post('/api/ancillaries/apply', body); }
  finally{ a.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  const keep = body.action === 'delete' ? '' : body.ancillary;
  await loadAncillaries();
  if(keep) anOpen(keep);
}
