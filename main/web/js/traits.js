/* traits.js - Traits mode: export_descr_character_traits.txt, both halves of it

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= TRAITS MODE =======================
   A trait is two things in two places. The top of the EDCT says what it IS - who
   can have it, which cultures cannot, and the ladder of levels with their
   effects. Hundreds of lines below, past `;== TRIGGER DATA ==`, the triggers say
   how anyone ever GETS it. Reading one without the other tells you nothing, so
   this screen shows them together: the levels above, and every trigger whose
   `Affects` names this trait below, in the shared builder from Phase 7.

   THE PAGE NEVER PARSES A GAME FILE. Everything here is /api/traits, /api/trait
   and /api/traits/plan|apply; the boxes are drawn from what the server read and
   a save posts back the same shape the server's own render_block takes.

   Three things the format imposes, all visible in this UI:

     * `Characters` accepts a comma list and the engine reads only the FIRST one,
       so this is a single picker with the bug spelled out, not a checklist that
       silently does nothing.
     * A level's five text fields are keys in data/text/export_VnVs.txt, and a
       character who reaches a level whose key is missing crashes the character
       screen. Missing keys are listed on the trait, and a save writes them.
     * Deleting a trait has to take its triggers with it - an `Affects` naming a
       trait that no longer exists is the "Trait not recognized" error. The
       confirmation says exactly which ones go. */

const TR_BLANK = {name:'', characters:['family'], hidden:false, exclude_cultures:[],
  no_going_back_level:'', anti_traits:[], levels:[]};

async function loadTraits(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ` + esc(mod) + `${tt('traits.s_traits')}</div>`;
  let r;
  try{ r = await api.get('/api/traits?mod=' + enc(mod)); }
  catch(e){ if(stale('traits', mod)) return;
    main.innerHTML = `<div class="empty">${tt('traits.couldnt_read_the_traits_file')}<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadTraits()">${tt('common.retry')}</button></div>`; return; }
  if(stale('traits', mod)) return;
  state.tr = Object.assign({sel:'', d:null, busy:false, adding:false}, r);
  undoReset();
  renderTraits();
}

function renderTraits(){
  const t = state.tr;
  if(!t){ loadTraits(); return; }
  const strip = minorTabsHtml('', 'data/export_descr_character_traits.txt');
  if(t.error || !t.exists){
    main.innerHTML = strip + `<div class="empty">${tt('traits.traits_live_in_data_export_descr',{error:esc(t.error || tt('traits.no_traits_file'))})}</div>`;
    return;
  }
  const rows = trRows();
  count.textContent = `${rows.length}/${t.count}`;
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      <div class="trnewrow">
        <button class="trnew" onclick="trNew()">${tt('traits.new_trait')}</button>
        <button class="trnew" onclick="portOpen('traits')" title="${ttA('traits.copy_traits_out_of_another_mod')}">${tt('traits.port_from_another_mod')}</button>
      </div>
      ${findingsHtml('traits', t.finding_list, 'trOpen')}
      <div class="trrows">${rows.map(trRowHtml).join('')
        || `<div class="count" style="padding:8px">${tt('traits.no_trait_matches')}</div>`}</div>
    </div>
    <div class="trmain" id="trMain">${trDetailHtml()}</div>
  </div>`;
}

// The list is filtered in the page, not on the server: 800 rows is a list, and
// the whole file was parsed once to build it anyway (unlike names.txt's 20 757,
// which is why Strings pages server-side and this does not).
function trRows(){
  const q = search.value.trim().toLowerCase();
  const rows = state.tr.traits || [];
  if(!q) return rows;
  return rows.filter(r => r.name.toLowerCase().includes(q)
    || (r.label||'').toLowerCase().includes(q));
}

function trRowHtml(r){
  const on = state.tr.sel === r.name;
  return `<button class="trrow${on?' on':''}" onclick="trOpen('${q1(esc(r.name))}')">
    <div class="nm">${esc(r.label)}</div>
    <div class="sub">${ttN('traits.level_count',r.levels,{hidden:r.hidden?tt('traits.hidden'):'',x:r.triggers?ttN('traits.trigger_count_suffix',r.triggers)
        :r.lua_gives?tt('traits.given_by_a_script'):` ${tt('traits.no_trigger_gives_it',{lua_names:r.lua_names?tt('traits.a_script_names_it'):''})}`,findings:r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''})}</div>
  </button>`;
}

async function trOpen(name){
  activity(tt('traits.opened_trait'), `${name} in ${state.src}`);
  const t = state.tr;
  t.sel = name; t.adding = false; t.d = null;
  renderTraits();
  let d;
  try{ d = await api.get(`/api/trait?mod=${enc(t.mod)}&name=${enc(name)}`); }
  catch(e){ d = {error:''+e}; }
  if(state.mode !== 'traits' || state.tr !== t || t.sel !== name) return;
  t.d = d.error ? d : trWorking(d);
  undoReset();          // the working copy exists now: this is Ctrl+Z's baseline
  trPaint();
  // the pane is remembered across records and modules; fetched after the first
  // paint so it never delays the form
  if(!d.error && state.settings.code_view) trCvToggle();
}

/* The working copy the boxes are bound to. Kept beside the payload the server
   sent so a save can post the whole form and the server can write only the lines
   that actually differ - which is what keeps a save from reformatting 20 lines
   the user never touched. */
function trWorking(d){
  d.w = JSON.parse(JSON.stringify(d.trait));
  d.trigs = (d.triggers || []).map(t => ({name:t.name, ui:null, dirty:false, src:t}));
  d.dirty = false;
  return d;
}

function trNew(){
  const t = state.tr;
  t.sel = ''; t.adding = true;
  t.d = {name:'', label:tt('traits.new_trait_2'), trait:JSON.parse(JSON.stringify(TR_BLANK)),
    w:Object.assign(JSON.parse(JSON.stringify(TR_BLANK)),
      {levels:[trBlankLevel('')]}),
    trigs:[], findings:[], loc:{}, missing_loc:[], triggers:[], dirty:true,
    known:(t.traits||[]).map(r=>r.name),
    attributes:t.attributes||[], character_types:t.character_types||[]};
  renderTraits();
}

const trBlankLevel = name => ({name:name||'', description:'', effects_description:'',
  gain_message:'', lose_message:'', epithet:'', threshold:'1', effects:[]});

function trPaint(){
  const el = document.getElementById('trMain');
  if(el) el.innerHTML = trDetailHtml();
  const d = state.tr.d;
  if(d && d.cv){ cvWire(d.cv); cvBindHover(d.cv, document.getElementById('trGui')); }
  trWireTriggers();
}

// The form only - never the pane, which has the caret in it.
function trPaintForm(){
  const d = state.tr.d, el = document.getElementById('trGui');
  if(!d || !el) return;
  el.innerHTML = trFindingsHtml(d) + trHeaderHtml(d.w, d) + trLevelsHtml(d.w, d);
  if(d.cv) cvBindHover(d.cv, el);
}

/* ---- the detail pane ---- */
function trDetailHtml(){
  const t = state.tr, d = t.d;
  if(!t.sel && !t.adding) return `<div class="empty">${tt('traits.pick_a_trait_counts',{traits:ttN('traits.trait_count',t.count),triggers:ttN('traits.trigger_count',t.triggers),file:esc(t.file)})}</div>`;
  if(!d) return `<div class="empty">${tt('traits.reading_the_trait')}</div>`;
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  const w = d.w;
  return `<div class="trbar">
      <div><b>${esc(t.adding ? tt('traits.new_trait_3') : d.label)}</b>
        <span class="count">${ttN('traits.level_count_plain',w.levels.length)}</span></div>
      <span class="sp"></span>
      ${t.adding ? '' : `<button class="${d.cv?'on':''}" title="${ttA('traits.show_this_trait_exactly_as_export')}"
        onclick="trCvToggle()">${tt('common.code_view')}</button>
      <button class="danger" onclick="trDelete()">${tt('common.delete')}</button>`}
      <button class="primary" onclick="trSave()">${t.adding?tt('traits.create_trait'):tt('common.save')}</button>
    </div>
    <div id="trGui">
      ${trFindingsHtml(d)}
      ${trHeaderHtml(w, d)}
      ${trLevelsHtml(w, d)}
    </div>
    ${trCvHtml()}
    ${trTriggersHtml(d)}`;
}

function trFindingsHtml(d){
  const out = [];
  if((d.findings||[]).length) out.push(...d.findings.map(f =>
    `<div class="trfind w-warn">${tt('traits.line',{line:f.line,message:esc(f.message)})}</div>`));
  if((d.missing_loc||[]).length) out.push(`<div class="trfind w-warn">${tt('traits.text_key_s_are_not_in',{missing_loc_n:d.missing_loc.length,missing_loc:d.missing_loc.slice(0,4).map(esc).join(', '),missing_loc2:d.missing_loc.length>4?'…':''})}</div>`);
  return out.join('');
}

function trHeaderHtml(w, d){
  const types = d.character_types || ['family'];
  return `<section class="trsec">
    <div class="trsechead">${tt('traits.header_the_order_of_these_lines')}</div>
    <div class="trgrid">
      <label class="lbl" data-label="name">${tt('common.name')}</label>
      <input data-label="name" value="${esc(w.name)}" ${state.tr.adding?'':'disabled'}
        placeholder="${ttA('traits.traitname')}" oninput="trSet('name',this.value)">
      <label class="lbl" data-label="characters">${tt('common.characters')}</label>
      <div data-label="characters">
        <select onchange="trSet('characters',[this.value])">${
          types.map(c=>`<option ${c===(w.characters[0]||'family')?'selected':''}>${
            esc(c)}</option>`).join('')}</select>
        ${w.characters.length>1?`<div class="trhint w-warn">${tt('traits.this_trait_lists_and_the_engine',{characters:esc(w.characters.join(', '))})}</div>`:''}
      </div>
      <label class="lbl" data-label="hidden">${tt('traits.hidden_2')}</label>
      <div data-label="hidden"><label class="chk"><input type="checkbox" ${w.hidden?'checked':''}
        onchange="trSet('hidden',this.checked)"> ${tt('traits.not_shown_on_the_character_screen')}</label></div>
      <label class="lbl" data-label="exclude_cultures">${tt('traits.excludecultures')}</label>
      <input data-label="exclude_cultures" value="${esc(w.exclude_cultures.join(', '))}"
        placeholder="${ttA('common.none')}"
        oninput="trSet('exclude_cultures',this.value.split(',').map(s=>s.trim()).filter(Boolean))">
      <label class="lbl" data-label="no_going_back_level">${tt('traits.nogoingbacklevel')}</label>
      <input data-label="no_going_back_level" value="${esc(w.no_going_back_level)}"
        placeholder="${ttA('common.none')}" style="width:90px"
        oninput="trSet('no_going_back_level',this.value.trim())">
      <label class="lbl" data-label="anti_traits">${tt('traits.antitraits')}</label>
      <div data-label="anti_traits">
        <input value="${esc(w.anti_traits.join(', '))}" placeholder="${ttA('common.none')}" list="trAnti"
          oninput="trSet('anti_traits',this.value.split(',').map(s=>s.trim()).filter(Boolean))">
        <datalist id="trAnti">${(d.known||[]).map(n=>`<option value="${esc(n)}">`).join('')}</datalist>
      </div>
    </div>
  </section>`;
}

function trLevelsHtml(w, d){
  return `<section class="trsec">
    <div class="trsechead">${tt('traits.levels_a_character_climbs_these_as')}</div>
    ${w.levels.map((lv,i)=>trLevelHtml(lv,i,d)).join('')
      || `<div class="count" style="padding:6px">${tt('traits.no_levels_so_this_trait_can')}</div>`}
    ${w.levels.length<9?`<button class="trgadd" onclick="trAddLevel()">${tt('traits.add_level')}</button>`:''}
  </section>`;
}

/* A level is a key on the left and the words the player reads on the right.
   The key is in the EDCT, the words are in data/text/export_VnVs.txt, and a key
   with no entry crashes the character screen - so both are edited here, in one
   row, and one save writes both files. */
function trLevelHtml(lv, i, d){
  const key = `level#${i+1}`;
  /* The key on the left and the words on the right, and the words box is bound
     to the SLOT rather than to the key it happens to hold right now. Binding it
     to the key baked the key in at paint time, and a level's key box does not
     repaint as it is typed into - so on a new trait the words landed under the
     empty tag, never reached the save, and the level was written with its own
     code name as its text. Same reason the box is always drawn: a key typed
     into an empty box would otherwise have no words box beside it until
     something else redrew the form. */
  const txt = (k, label, hint) => {
    const tag = (lv[k] || '').trim();
    return `<label class="lbl" data-label="${key}.${k}">${label}</label>
    <div class="trkey">
      <input data-label="${key}.${k}" value="${esc(lv[k]||'')}"
        placeholder="${esc(hint||'none')}"
        oninput="trSetLevel(${i},'${k}',this.value.trim())">
      <input class="trtext" value="${esc(trLocTextAt(d, i, k))}"
        placeholder="${tag ? (trHasKey(d, tag)?'':tt('traits.not_in_export_vnvs_txt_yet'))
                           : tt('traits.name_the_key_on_the_left')}"
        title="${ttA('traits.what_the_player_reads_saved_into')}"
        oninput="trSetLocAt(${i},'${k}',this.value)">
    </div>`;
  };
  return `<div class="trlevel" data-card="${key}">
    <div class="trlevhead">
      <span class="n">${i+1}</span>
      <input class="trlevname" data-label="${key}.name" value="${esc(lv.name)}"
        placeholder="${ttA('traits.levelname')}" oninput="trSetLevel(${i},'name',this.value.trim())">
      <input class="trtext" value="${esc(trLocTextAt(d, i, 'name'))}"
        placeholder="${lv.name ? (trHasKey(d, lv.name)?'':tt('traits.the_name_on_the_character_screen'))
                               : tt('traits.name_the_level_first')}"
        title="${ttA('traits.the_levels_name_as_the_player')}"
        oninput="trSetLocAt(${i},'name',this.value)">
      <span class="lbl" data-label="${key}.threshold">${tt('traits.threshold')}</span>
      <input class="trnum" data-label="${key}.threshold" value="${esc(lv.threshold)}"
        oninput="trSetLevel(${i},'threshold',this.value.trim())">
      <button class="trgdel" title="${ttA('traits.remove_this_level')}"
        onclick="trDelLevel(${i})">✕</button>
    </div>
    <div class="trgrid">
      ${txt('description',tt('common.description'), lv.name?lv.name+'_desc':'')}
      ${txt('effects_description','EffectsDescription', lv.name?lv.name+'_effects_desc':'')}
      ${txt('gain_message','GainMessage')}
      ${txt('lose_message','LoseMessage')}
      ${txt('epithet',tt('traits.epithet'))}
    </div>
    <div class="treffects">
      ${(lv.effects||[]).map((e,k)=>trEffectHtml(e,i,k,d)).join('')}
      <button class="trgadd" onclick="trAddEffect(${i})">${tt('traits.add_effect')}</button>
    </div>
  </div>`;
}

// An attribute the engine does not have is marked but never refused: M2TWEOP
// adds some, and the generated list is what the mods and the Docudemons sheet
// between them know about - not a spec.
function trEffectHtml(e, i, k, d){
  const attrs = d.attributes || [];
  const known = !e.attribute || attrs.includes(e.attribute)
    || /^Combat_V_(Faction|Religion)_./.test(e.attribute);
  return `<div class="treff" data-label="level#${i+1}.effect#${k+1}">
    <input class="trattr${known?'':' bad'}" value="${esc(e.attribute)}" list="trAttrs"
      placeholder="${ttA('traits.attribute')}"
      oninput="trSetEffect(${i},${k},'attribute',this.value.trim())">
    <input class="trnum" value="${esc(e.amount)}"
      oninput="trSetEffect(${i},${k},'amount',this.value.trim())">
    ${known?'':`<span class="count w-warn">${tt('traits.not_a_character_attribute')}</span>`}
    <button class="trgdel" onclick="trDelEffect(${i},${k})">✕</button>
    <datalist id="trAttrs">${attrs.map(a=>`<option value="${esc(a)}">`).join('')}</datalist>
  </div>`;
}

/* ---- the triggers that feed this trait ----
   The other half of what a trait is. Each one is the shared builder from Phase 7
   (web/js/triggerui.js), which is why that file has waited for this screen. */
function trTriggersHtml(d){
  if(state.tr.adding) return `<section class="trsec">
    <div class="trsechead">${tt('common.triggers')}</div>
    <div class="count" style="padding:6px">${tt('traits.create_the_trait_first_then_add')}</div></section>`;
  return `<section class="trsec">
    <div class="trsechead">${tt('common.triggers')} <span class="count">${d.trigs.length
      ? tt('traits.what_gives_this_trait_its_points')
      : luaGives(d.lua) ? tt('traits.no_trigger_a_script_gives_it')
      : tt('traits.nothing_gives_this_trait_any_points')}</span></div>
    ${luaHitsHtml(d.lua, 'trait')}
    ${d.trigs.map((t,i)=>`<div class="trtrig">
      <div class="trtrighead">
        <b>${esc(t.name)}</b>
        <span class="sp"></span>
        <button class="trgdel" title="${ttA('common.remove_this_trigger')}"
          onclick="trDelTrigger(${i})">✕</button>
      </div>
      <div id="trtrg-${i}"></div>
    </div>`).join('')}
    <button class="trgadd" onclick="trAddTrigger()">${tt('common.add_trigger')}</button>
  </section>`;
}

// The builder is created after the markup exists, because it paints itself into
// a slot by id and loads its vocabulary asynchronously.
async function trWireTriggers(){
  const d = state.tr.d;
  if(!d || !d.trigs) return;
  for(let i = 0; i < d.trigs.length; i++){
    const slot = document.getElementById('trtrg-' + i);
    if(!slot) continue;
    const row = d.trigs[i];
    if(!row.ui){
      row.ui = trgCreate({mod:state.tr.mod, trigger:row.src,
        onChange:() => { row.dirty = true; trDirty(); }});
      await trgLoad(row.ui);
    }
    const here = document.getElementById('trtrg-' + i);
    if(here) here.innerHTML = trgHtml(row.ui);
  }
}

/* ---- edits ----
   State first, paint second. A change that alters the SHAPE of the form
   repaints; typing in a box does not, or the caret jumps out from under the
   user on every keystroke. */
function trSet(key, value){
  const d = state.tr.d; if(!d) return;
  d.w[key] = value;
  trDirty(key === 'hidden' || key === 'characters');
}
function trSetLevel(i, key, value){
  const d = state.tr.d, lv = d && d.w.levels[i]; if(!lv) return;
  lv[key] = value;
  trDirty(false);
}
/* What a key says on screen. `locEdits` is what has been retyped this session,
   keyed by the SLOT that was typed into (`3.description`) rather than by the key
   that slot held; `loc` is what the mod's text file says now.

   Keying by slot is what makes renaming a key carry its words with it, and what
   makes words typed beside a key that was itself typed this session reach the
   save at all - `trSetLevel` deliberately does not repaint, so a handler with
   the key baked into it goes on writing under the key the box held when the
   form was last drawn. The tags are resolved once, at save time, in
   `trLocBody`. */
const trHasKey = (d, tag) => tag && (d.loc||{})[tag] !== undefined;
const trSlot = (i, field) => i + '.' + field;
function trTagAt(d, i, field){
  const lv = d && d.w && d.w.levels[i];
  return lv ? String(lv[field] || '').trim() : '';
}
function trLocTextAt(d, i, field){
  const tag = trTagAt(d, i, field);
  if(!tag) return '';
  const e = (d.locEdits || {})[trSlot(i, field)];
  return e !== undefined ? e : ((d.loc||{})[tag] || '');
}
function trSetLocAt(i, field, value){
  const d = state.tr.d; if(!d) return;
  (d.locEdits = d.locEdits || {})[trSlot(i, field)] = value;
  trDirty(false);
}
// slot -> the key that slot names now. A slot whose key has been emptied writes
// nothing; two slots naming one key is the file's own doing, and the last wins.
function trLocBody(){
  const d = state.tr.d, out = {};
  for(const [slot, value] of Object.entries((d && d.locEdits) || {})){
    const cut = slot.indexOf('.');
    const tag = trTagAt(d, +slot.slice(0, cut), slot.slice(cut + 1));
    if(tag) out[tag] = value;
  }
  return out;
}
function trSetEffect(i, k, key, value){
  const d = state.tr.d, lv = d && d.w.levels[i]; if(!lv || !lv.effects[k]) return;
  lv.effects[k][key] = value;
  trDirty(false);
}
function trAddLevel(){
  const d = state.tr.d; if(!d) return;
  const n = d.w.levels.length;
  const last = d.w.levels[n-1];
  const name = (d.w.name || tt('traits.level_3')) + (n + 1);
  d.w.levels.push(Object.assign(trBlankLevel(name),
    {threshold:String((+(last && last.threshold) || 0) + 1)}));
  trDirty(true);
}
function trDelLevel(i){
  const d = state.tr.d; if(!d) return;
  d.w.levels.splice(i, 1);
  // the words typed this session are keyed by level INDEX, so the ones below the
  // removed level have to slide down with it - otherwise they would be written
  // out against the next level's keys
  const moved = {};
  for(const [slot, value] of Object.entries(d.locEdits || {})){
    const cut = slot.indexOf('.'), n = +slot.slice(0, cut);
    if(n === i) continue;
    moved[(n > i ? n - 1 : n) + slot.slice(cut)] = value;
  }
  d.locEdits = moved;
  trDirty(true);
}
function trAddEffect(i){
  const lv = state.tr.d.w.levels[i]; if(!lv) return;
  (lv.effects = lv.effects || []).push({attribute:'', amount:'1'});
  trDirty(true);
}
function trDelEffect(i, k){
  state.tr.d.w.levels[i].effects.splice(k, 1);
  trDirty(true);
}
function trAddTrigger(){
  const d = state.tr.d; if(!d) return;
  const n = (d.name || 'trait').toLowerCase() + '_' + (d.trigs.length + 1);
  d.trigs.push({name:n, ui:null, dirty:true, added:true,
    src:{name:n, when_to_test:'CharacterTurnEnd', conditions:[],
         effects:[{keyword:tt('traits.affects'), args:[d.name, '1', tt('traits.chance'), '100']}]}});
  trDirty(true);
}
function trDelTrigger(i){
  const d = state.tr.d;
  const row = d.trigs[i];
  if(!row.added && !confirm(tt('traits.remove_trigger_confirm',{name:row.name}))) return;
  if(row.ui) trgDrop(row.ui);
  d.trigs.splice(i, 1);
  d.removed = (d.removed || []).concat(row.added ? [] : [row.name]);
  trDirty(true);
}
function trDirty(repaint){
  const d = state.tr.d;
  d.dirty = true;
  if(repaint) trPaint();
  // the GUI→pane half of the Code View contract: change a box and the text pane
  // is re-serialised by the server, through the serialiser the save itself uses
  if(d.cv) cvFromGui(d.cv);
}

/* ---- one trait as the file writes it ----
   The same inline pane the unit and building editors use, remembered across
   records and modules by the one `code_view` setting. Text typed in the pane
   wins over the boxes when a save goes out (`raw_block`), because reordering,
   indenting and comments are edits no field map can express. */
function trCvHtml(){
  const d = state.tr.d;
  return d && d.cv ? `<div id="trCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : '';
}

async function trCvToggle(){
  const d = state.tr.d; if(!d) return;
  if(d.cv){ cvDrop(d.cv); d.cv = null; state.settings.code_view = false;
    api.post('/api/settings', {code_view:false}); trPaint(); return; }
  state.settings.code_view = true; api.post('/api/settings', {code_view:true});
  d.cv = cvCreate(trCvHost());
  trPaint();
  await cvLoad(d.cv);
  if(state.tr.d !== d || !d.cv) return;
  trPaint();
}

function trCvHost(){
  return {kind:'traits', mod:state.tr.mod, id:state.tr.d.name,
    where:'data/' + state.tr.file,
    edits:() => trEdits(),
    // The pane's own text becomes the truth once it has been typed into: it can
    // say things the boxes cannot (a comment, a reordered level), so the form
    // follows it and the save carries it verbatim.
    adopt:cv => { const d = state.tr.d;
      if(!cv.detail) return;
      d.w = cv.detail;
      // `base`, never `text`: with comment hiding on, `text` is the view with the
      // comment-only lines cut out of it, and saving that would delete every one
      // of them. `base` is the record's real bytes.
      d.raw = cv.edited ? cv.base : ''; },
    refreshGui:() => { trPaintForm(); }};
}

/* ---- writing ---- */
function trEdits(){
  const w = state.tr.d.w;
  return {name:w.name, characters:w.characters, hidden:w.hidden,
    exclude_cultures:w.exclude_cultures, no_going_back_level:w.no_going_back_level,
    anti_traits:w.anti_traits,
    levels:w.levels.map(lv => ({name:lv.name, description:lv.description,
      effects_description:lv.effects_description, gain_message:lv.gain_message,
      lose_message:lv.lose_message, epithet:lv.epithet, threshold:lv.threshold,
      effects:(lv.effects||[]).filter(e => e.attribute && e.amount)}))};
}

function trBody(action){
  const t = state.tr, d = t.d;
  const body = {mod:t.mod, trait:action === 'add' ? d.w.name : d.name, action};
  if(action !== 'delete'){
    body.edits = trEdits();
    body.loc = trLocBody();
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

async function trSave(){
  const t = state.tr, d = t.d;
  if(t.adding && !d.w.name.trim()){ toast(tt('traits.a_new_trait_needs_a_name'), 3500); return; }
  await trApply(trBody(t.adding ? 'add' : 'edit'),
                t.adding ? `create ${d.w.name}` : `save ${d.name}`);
}

async function trDelete(){
  const d = state.tr.d;
  await trApply(trBody('delete'), `delete ${d.name}`);
}

async function trApply(body, what){
  const t = state.tr;
  if(t.busy) return;
  t.busy = true;
  let plan;
  try{ plan = await api.post('/api/traits/plan', body); }
  finally{ t.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 6000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 14);
  const found = (p.findings || []).map(f => '⚠ ' + f.message);
  if(!confirm(tt('traits.write_confirm',{what,changes:lines.join('\n') || tt('common.no_visible_change'),
    more:(p.changes || []).length > 14 ? tt('traits.and_more',{changes:p.changes.length - 14}) : '',
    warnings:found.length ? '\n\n' + found.slice(0, 4).join('\n') : ''}))) return;
  t.busy = true;
  let res;
  try{ res = await api.post('/api/traits/apply', body); }
  finally{ t.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  const keep = body.action === 'delete' ? '' : body.trait;
  await loadTraits();
  if(keep) trOpen(keep);
}
