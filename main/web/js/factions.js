/* factions.js - Factions mode: descr_sm_factions.txt, the faction roster

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= FACTIONS MODE =======================
   What a faction IS: its culture and religion, the two colours it paints the
   campaign map with, the strat models it puts on it, what it may and may not do,
   and - for the few that have one - its horde.

   Four things about this screen that the file decided:

     * THE LOCALISED NAME MATTERS MORE HERE THAN ANYWHERE. Mods reuse vanilla
       slots wholesale, so DaC's `sicily` is the Kingdom of Gondor and its
       `turks` are somebody else again. A list of slots would be a list of the
       wrong countries; every row leads with the real name.
     * THE SLOT CANNOT BE RENAMED. descr_strat, every unit's ownership line,
       every `requires factions { … }` clause, descr_names and its own
       expanded.txt entry all point at it. The head line's modifier after the
       comma (`faction egypt, spawned_on_event`) is shown but not edited here.
     * ADD BY CLONING, NEVER DELETE. A faction lives in thirteen files at once,
       so one that exists only in this file is a mod that will not load - which
       is an argument for writing all thirteen, not for refusing. ＋ Add a faction
       copies a working faction into every one of them (factionclone.py).
       Deleting stays out: a clone copies the donor's answer, and a delete would
       have to invent one for every line that names the slot.
     * A MISSING PICTURE IS NOT A FAULT. `symbol` and `rebel_symbol` are .CAS 3D
       models, and not one of the 90 real factions measured ships its
       `loading_logo` unpacked - they are all inside the game's .pack archives.
       So the paths are shown and a found one is marked; an unfound one is not
       called missing.

   The colours ARE ours to show, and they are the only genuinely visual thing in
   the file: `primary_colour red 55, green 75, blue 48` gets a swatch and a picker.

   THE PAGE NEVER PARSES A GAME FILE: /api/factions, /api/faction,
   /api/factions/plan|apply and /api/factions/clone_plan|clone_apply do all of
   it - including working out which thirteen files a new faction would change. */

/* The roster, into `state.fac`, without drawing anything.

   17f put this form on two screens: its own mode, and the campaign map's
   faction screen, where the same faction's `descr_strat.txt` half is edited
   beside it. Only the mode owns `main`, so the read and the drawing are two
   things now - the panel calls this and paints itself. */
async function facFetch(mod){
  const r = await api.get('/api/factions?mod=' + enc(mod));
  const keep = (state.fac && state.fac.mod === mod) ? state.fac.sel : '';
  state.fac = Object.assign({sel: keep, d: null, busy: false}, r);
  return state.fac;
}

async function loadFactions(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ` + esc(mod) + `${tt('factions.s_factions')}</div>`;
  try{ await facFetch(mod); }
  catch(e){ if(stale('factions', mod)) return;
    main.innerHTML = `<div class="empty">${tt('factions.couldnt_read_the_faction_roster')}<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadFactions()">${tt('common.retry')}</button></div>`; return; }
  if(stale('factions', mod)) return;
  state.fac.sel = '';
  undoReset();
  renderFactions();
}

function renderFactions(){
  const f = state.fac;
  if(!f){ loadFactions(); return; }
  const strip = minorTabsHtml('', 'data/descr_sm_factions.txt');
  if(f.error || !f.exists){
    main.innerHTML = strip + `<div class="empty">${tt('factions.it_lives_in_data_descr_sm',{x:esc(f.error || tt('factions.no_faction_roster'))})}</div>`;
    return;
  }
  const rows = facRows();
  count.textContent = `${rows.length}/${f.count}`;
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('factions', f.finding_list, 'facOpen')}
      <div class="trnote">${tt('factions.faction_files',{x:f.limit ? tt('factions.faction_slots_used',{count:f.count,limit:f.limit})
        : tt('factions.faction_slots_this_mod_is_marked',{count:f.count,VANILLA_FACTION_LIMIT}),x2:f.can_clone ? `<button class="fcadd" onclick="facCloneOpen()"
          ${facFull() ? 'disabled' : ''} title="${facFull()
            ? tt('factions.every_faction_slot_the_engine_has')
            : tt('factions.add_a_faction_by_copying_one')}"
          >${tt('factions.add_a_faction')}</button>` : '',x3:enc(state.src),x4:f.sel ? '&art=' + enc(fcSlotOf(f.sel)) : '',x5:f.sel ? tt('factions.with_the_art_of_the_faction') : ''})}</div>
      <div class="trrows">${rows.map(facRowHtml).join('')
        || `<div class="count" style="padding:8px">${tt('factions.no_faction_matches')}</div>`}</div>
    </div>
    <div class="trmain">${f.sel && typeof fauHost === 'function' ? fauHost() : ''}
      <div id="facMain">${facDetailHtml()}</div></div>
  </div>`;
}

function facRows(){
  const q = search.value.trim().toLowerCase();
  const rows = state.fac.factions || [];
  if(!q) return rows;
  return rows.filter(r => r.slot.toLowerCase().includes(q)
    || (r.label||'').toLowerCase().includes(q)
    || (r.culture||'').toLowerCase().includes(q)
    || (r.religion||'').toLowerCase().includes(q));
}

function facRowHtml(r){
  const on = state.fac.sel === r.name;
  return `<button class="trrow facrow2${on?' on':''}"
      onclick="facOpen('${q1(esc(r.name))}')">
    <span class="facswatch"><i style="background:${esc(r.primary||'#333')}"></i
      ><i style="background:${esc(r.secondary||'#333')}"></i></span>
    <span class="antxt">
      <span class="nm">${esc(r.label)}</span>
      <span class="sub">${esc(r.culture||tt('factions.no_culture'))} · ${esc(r.religion||tt('factions.no_religion'))}${
        r.horde?tt('factions.horde_of',{horde:r.horde}):''}${
        r.special?` · ${esc(r.special)}`:''}${
        r.modifier?` · ${esc(r.modifier)}`:''}${
        r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''}</span>
    </span>
  </button>`;
}

//: The two screens this form is drawn on (17f), and which of them is up. The
//: mode owns the whole page; the campaign map's faction screen owns one div in
//: the middle of a panel, so the paint target is asked for rather than assumed.
function facHosted(){ return state.mode === 'factions' || state.mode === 'campmap'; }

async function facOpen(name){
  activity(tt('factions.opened_faction'), `${name} in ${state.src}`);
  const f = state.fac;
  if(!f) return;
  f.sel = name; f.d = null;
  if(state.mode === 'factions') renderFactions(); else facPaint();
  let d;
  try{ d = await api.get(`/api/faction?mod=${enc(f.mod)}&name=${enc(name)}`); }
  catch(e){ d = {error:''+e}; }
  if(!facHosted() || state.fac !== f || f.sel !== name) return;
  f.d = d.error ? d : facWorking(d);
  undoReset();          // the working copy exists now: this is Ctrl+Z's baseline
  facPaint();
  if(!d.error && state.settings.code_view) facCvToggle();
}

function facWorking(d){
  d.w = JSON.parse(JSON.stringify(d.faction));
  // which lines the record actually HAS: an emptied one of these deletes its
  // line, and a key not in here that gains a value is inserted at its canonical
  // place in the file's own order (the server's edit_keys does that placing).
  d.had = new Set((d.vocab.order||[]).filter(k => (d.w[k]||'') !== ''));
  d.locEdits = {};
  return d;
}

function facPaint(){
  const el = document.getElementById('facMain');
  if(el) el.innerHTML = facDetailHtml();
  const d = state.fac && state.fac.d;
  if(d && d.cv){ cvWire(d.cv); cvBindHover(d.cv, document.getElementById('facGui')); }
}

function facPaintForm(){
  const d = state.fac.d, el = document.getElementById('facGui');
  if(!d || !el) return;
  el.innerHTML = facFindingsHtml(d) + facFormHtml(d);
  if(d.cv) cvBindHover(d.cv, el);
}

/* ---- the detail pane ---- */
function facDetailHtml(){
  const f = state.fac, d = f.d;
  if(!f.sel) return `<div class="empty">${ttN('factions.pick_a_faction_counted', f.count, {file:esc(f.file)})}
    <div class="trnote" style="max-width:600px;margin:14px auto;text-align:left">${
      esc(f.refused)}</div></div>`;
  if(!d) return `<div class="empty">${tt('factions.reading_the_faction')}</div>`;
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  return `<div class="trbar">
      <div><b>${esc(d.label)}</b>
        <span class="count">${esc(d.faction.culture||'')}${
          d.modifier?' · '+esc(d.modifier):''}</span></div>
      <span class="sp"></span>
      <button title="${ttA('factions.rename_this_slot_in_every_file')}"
        onclick="facRename()">${tt('factions.rename_slot')}</button>
      <button class="${d.cv?'on':''}" title="${ttA('factions.show_this_faction_exactly_as_descr')}"
        onclick="facCvToggle()">${tt('common.code_view')}</button>
      <button class="primary" onclick="facSave()">${tt('common.save')}</button>
    </div>
    <div id="facGui">
      ${facFindingsHtml(d)}
      ${facFormHtml(d)}
    </div>
    ${d.cv ? `<div id="facCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : ''}`;
}

/* ---- renaming the slot (19b, D3) ----

   The Code View has refused this since 15g, and the refusal named the cost
   exactly: a slot is what descr_strat, every unit's ownership line, every
   `requires factions { … }` clause and its own text entry point at. That was
   right about the problem. `unittransfer/renames.py` does all of them, and the
   dialog shows the list before there is a button, because in a real mod the list
   is twenty-four files and four thousand lines.

   Not a field on this form: renaming rewrites files this screen has never
   opened, so it is its own save, its own backup set and its own undo. */
function facRename(){
  const f = state.fac, d = f && f.d;
  if(!d || d.error) return;
  renameOpen(f.mod, 'faction', fcSlotOf(d.faction.name), async (name) => {
    await loadFactions();              // the roster, the art and the labels moved
    await facOpen(name);
  });
}

function facFindingsHtml(d){
  const out = (d.findings||[]).map(f =>
    `<div class="trfind w-warn">${tt('factions.line',{line:f.line,message:esc(f.message)})}</div>`);
  if((d.missing_loc||[]).length) out.push(`<div class="trfind w-warn">
    ${tt('factions.there_is_no_entry_in_so',{loc_tag:esc(d.loc_tag),loc_file:esc(d.loc_file)})}</div>`);
  return out.join('');
}

/* ---- the form ---- */
/* ---- five tabs over one record (Phase 46) ----
   The form was one long scroll of five sections that were already separate:
   the record, the pictures, what it can do, the movies and the horde. The same
   strip as the Cultures form, no parser work: a tab is only which section is
   drawn. The chosen tab is remembered across factions. */
const FAC_TABS = [['general',tt('common.general')], ['art',tt('factions.art_and_banners')], ['abilities',tt('factions.what_it_can_do')],
                  ['movies',tt('factions.movies')], ['horde',tt('factions.horde')]];
function facTab(id){ state.facTab = id; facPaintForm(); }
function facFormHtml(d){
  const cur = state.facTab || 'general';
  const strip = recTabsHtml(FAC_TABS, cur, 'facTab');
  const body = cur === 'art' ? facArtSection(d) : cur === 'abilities' ? facAbilitySection(d)
    : cur === 'movies' ? facMovies(d) : cur === 'horde' ? facHorde(d) : facGeneralSection(d);
  return strip + (body || `<div class="empty" style="padding:18px">${tt('factions.nothing_on_this_tab_for_this')}</div>`);
}
function facGeneralSection(d){
  const w = d.w, v = d.vocab || {};
  const shownName = d.locEdits[d.loc_tag] !== undefined
    ? d.locEdits[d.loc_tag] : ((d.loc||{})[d.loc_tag] || '');
  return `<section class="trsec">
    <div class="trsechead">${tt('factions.the_faction_the_line_order_here')}</div>
    <div class="trgrid">
      <label class="lbl" data-label="name">${tt('factions.slot')}</label>
      <div class="trkey">
        <input data-label="name" value="${esc(d.slot)}" disabled
          title="${ttA('factions.the_faction_slot_descr_strat_every')}">
        <input class="trtext" value="${esc(shownName)}"
          placeholder="${((d.loc||{})[d.loc_tag] === undefined)
            ? tt('factions.not_in_file_yet',{loc_file:esc(d.loc_file)}) : tt('factions.the_factions_name_in_game')}"
          title="${ttA('factions.what_the_player_reads_saved_into',{loc_file:esc(d.loc_file)})}"
          oninput="facSetLoc(this.value)">
      </div>
      ${d.modifier ? `<label class="lbl">${tt('factions.head_modifier')}</label>
        <div><input value="${esc(d.modifier)}" disabled>
        <div class="trhint count">${tt('factions.carried_on_the_faction_line_itself')}</div></div>` : ''}
      ${facPick(d, 'culture', tt('common.culture'), v.cultures)}
      ${facPick(d, 'religion', tt('factions.religion'), v.religions)}
      ${facColour(d, 'primary_colour', tt('factions.primary_colour'))}
      ${facColour(d, 'secondary_colour', tt('factions.secondary_colour'))}
      ${facPick(d, 'special_faction_type', tt('factions.special_type'), v.special_types, true)}
    </div>
  </section>`;
}
function facArtSection(d){
  const v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">${tt('factions.art_and_banners_symbol_lines_name')}</div>
    ${facPictures(d)}
    <div class="trgrid">
      ${(v.art_keys||[]).map(k => facArt(d, k)).join('')}
      ${facBox(d, 'standard_index', tt('factions.banner_index'))}
      ${facLogo(d, 'logo_index', tt('factions.logo_index'), v.logo_sprites, v.logo_indexes)}
      ${facLogo(d, 'small_logo_index', tt('factions.small_logo_index'), v.small_logo_sprites, v.small_logo_indexes)}
      ${facBox(d, 'triumph_value', tt('factions.triumph_value'))}
    </div>
  </section>`;
}
function facAbilitySection(d){
  const v = d.vocab || {};
  return `<section class="trsec">
    <div class="trsechead">${tt('factions.what_it_can_do')}</div>
    <div class="trgrid">
      ${(v.yes_no||[]).map(k => facYesNo(d, k)).join('')}
      ${facPick(d, 'has_family_tree', 'has_family_tree', v.family_tree)}
    </div>
    <div class="trhint count">${tt('factions.has_family_tree_is_not_a')}</div>
  </section>`;
}

const facHas = (d, k) => (d.w[k] || '') !== '';

function facBox(d, key, label, list){
  const id = 'facdl-' + key;
  return `<label class="lbl" data-label="${key}">${esc(label)}</label>
    <div><input data-label="${key}" value="${esc(d.w[key]||'')}"
      ${list&&list.length?tt('factions.list',{id}):''}
      oninput="facSet('${key}',this.value.trim())">
    ${list&&list.length?`<datalist id="${id}">${list.map(x =>
      `<option value="${esc(x)}">`).join('')}</datalist>`:''}</div>`;
}

//: 91: a shield is a sprite name in ui/strategy.sd or ui/shared.sd. When the mod
//: ships the sheet, only its names are offered and one that is not in it says
//: so; when the sheet is packed there is nothing to hold it against.
function facLogo(d, key, label, sprites, used){
  return sprites && sprites.length
    ? facPick(d, key, label, sprites, false, true)
    : facBox(d, key, label, used);
}

function facPick(d, key, label, options, optional, sheet){
  const cur = d.w[key] || '', opts = options || [];
  return `<label class="lbl" data-label="${key}">${esc(label)}</label>
    <div><select data-label="${key}" onchange="facSet('${key}',this.value)">
      ${optional?`<option value=""${cur?'':' selected'}>${tt('common.none_2')}</option>`:''}
      ${opts.map(o => `<option value="${esc(o)}"${o===cur?' selected':''}>${esc(o)}</option>`).join('')}
      ${cur && !opts.includes(cur)
        ? `<option value="${esc(cur)}" selected>${sheet ? tt('factions.not_in_the_sheet',{cur:esc(cur)}) : tt('factions.not_in_this_mod',{cur:esc(cur)})}</option>` : ''}
    </select></div>`;
}

function facYesNo(d, key){
  const cur = d.w[key] || '';
  if(!facHas(d, key) && !d.had.has(key)) return '';
  return `<label class="lbl" data-label="${key}">${esc(key)}</label>
    <div><select data-label="${key}" onchange="facSet('${key}',this.value)">
      ${['yes','no'].map(o => `<option value="${esc(o)}"${o===cur?' selected':''}>${esc(o)}</option>`).join('')}
      ${cur && cur!=='yes' && cur!=='no'
        ? `<option value="${esc(cur)}" selected>${tt('factions.not_yes_or_no',{cur:esc(cur)})}</option>` : ''}
    </select></div>`;
}

/* The two colours, as a swatch and a hex code.

   Two things this row must not do. It must not REPAINT while the swatch is
   being used: the OS colour picker is anchored to that very `<input>`, and
   `oninput` fires on every drag through the gradient - rebuilding the form under
   it replaced the element and shut the picker, so a colour could only be chosen
   one blind click at a time. So the swatch writes straight into the record and
   updates its two siblings by hand, and nothing here re-renders.

   And it must offer the hex, because hex is what a palette, an image editor and
   every other tool on the internet hand you. The file's own words (`red 55,
   green 75, blue 48`) stay on show underneath - that is what is written to disk,
   and the code view edits it verbatim - but they are not what anyone wants to
   type. Either box drives the other. */
function facColour(d, key, label){
  const hex = (d.colours||{})[key] || '#000000';
  return `<label class="lbl" data-label="${key}">${esc(label)}</label>
    <div>
      <div class="faccol">
        <input type="color" id="fcs_${key}" value="${esc(hex)}"
          title="${ttA('factions.pick_a_colour_the_box_stays')}"
          oninput="facSetColour('${key}',this.value)">
        <input class="faccolt" id="fch_${key}" value="${esc(hex)}"
          spellcheck="false" maxlength="7" placeholder="#rrggbb"
          title="${ttA('factions.the_colour_as_a_hex_code')}"
          oninput="facSetHex('${key}',this.value)">
      </div>
      <div class="trhint count" id="fcr_${key}">${esc(d.w[key]||'')}</div>
    </div>`;
}
//: `#rgb` and `#rrggbb`, with or without the hash - what a paste actually looks like
const FAC_HEX = /^#?(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;
function facHexFull(text){
  const s = (text||'').trim().replace(/^#/,'');
  if(!FAC_HEX.test(s)) return '';
  return '#' + (s.length === 3 ? s.split('').map(c => c + c).join('') : s).toLowerCase();
}

/* The faction's pictures. The roster names none of them (see factions.py), so
   they are found where the game itself looks - and a mod that keeps its art in
   a .pack archive simply has none to show, which is not a fault. */
function facPictures(d){
  const pics = d.pictures || [];
  if(!pics.length) return `<div class="trhint count" style="margin-bottom:8px">
    ${tt('factions.no_unpacked_pictures_for_normal_most',{slot:esc(d.slot)})}</div>`;
  return `<div class="facpics">${pics.map(p => {
    const url = `/icon?mod=${enc(state.fac.mod)}&kind=faction&rel=${enc(p.rel)}${iconBust()}`;
    return `<figure>
      <div class="icowrap"><img loading="lazy" onerror="iconRetry(this)"
        title="${ttA('common.replace_this_picture')}" onclick="imgPick('${q1(esc(url))}','facPaint')"
        src="${url}" alt="">${imgEditBtn(url,'facPaint')}</div>
      <figcaption>${esc(p.label)}<span class="count">${esc(p.rel)}</span>
        ${imgRow(url,'facPaint')}</figcaption>
    </figure>`;}).join('')}</div>`;
}

function facArt(d, key){
  const found = (d.art_found||{})[key];
  return `<label class="lbl" data-label="${key}">${esc(key)}</label>
    <div><input data-label="${key}" value="${esc(d.w[key]||'')}"
      oninput="facSet('${key}',this.value.trim())">
      <div class="trhint count">${found
        ? tt('factions.found_in_this_mod')
        : tt('factions.not_unpacked_here_normally_that_means')}</div>
    </div>`;
}

function facMovies(d){
  const keys = ['intro_movie','victory_movie','defeat_movie','death_movie'];
  const any = keys.some(k => d.had.has(k) || facHas(d, k));
  if(!any) return `<section class="trsec">
    <div class="trsechead">${tt('factions.movies_this_faction_has_none_and')}</div>
    <button class="trgadd" onclick="facAddGroup('movies')">${tt('factions.add_the_four_movie_lines')}</button>
  </section>`;
  return `<section class="trsec">
    <div class="trsechead">${tt('factions.movies_bik_files_under_data')}</div>
    <div class="trgrid">${keys.map(k => facBox(d, k, k)).join('')}</div>
  </section>`;
}

function facHorde(d){
  const v = d.vocab || {}, keys = v.horde_keys || [];
  const any = keys.some(k => d.had.has(k) || facHas(d, k));
  if(!any) return `<section class="trsec">
    <div class="trsechead">${tt('factions.horde_this_faction_has_none')}</div>
    <button class="trgadd" onclick="facAddGroup('horde')">${tt('factions.make_this_a_horde_faction')}</button>
  </section>`;
  const units = d.w.horde_units || [];
  return `<section class="trsec">
    <div class="trsechead">${tt('factions.horde_the_eight_settings_only_mean')}</div>
    <div class="trgrid">${keys.map(k => facBox(d, k, k)).join('')}</div>
    <div class="treffects">
      <div class="trsechead" style="margin:8px 0 0">${tt('factions.horde_units_what_it_spawns_when',{units_n:units.length})}</div>
      ${units.map((u,k)=>`<div class="treff" data-label="horde_unit#${k+1}">
        <input class="trattr" value="${esc(u)}" list="facUnits" placeholder="${ttA('factions.unit_type')}"
          oninput="facSetUnit(${k},this.value)">
        <span class="count">${esc(facUnitLabel(d, u))}</span>
        <button class="trgdel" onclick="facDelUnit(${k})">✕</button>
      </div>`).join('')}
      <datalist id="facUnits">${(v.units||[]).map(u =>
        `<option value="${esc(u.type)}">${esc(u.label)}</option>`).join('')}</datalist>
      <button class="trgadd" onclick="facAddUnit()">${tt('factions.add_horde_unit')}</button>
    </div>
  </section>`;
}

function facUnitLabel(d, type){
  if(!type) return '';
  const hit = ((d.vocab||{}).units||[]).find(u => u.type === type);
  return hit ? hit.label : tt('factions.not_a_unit_in_this_mod');
}

/* ---- edits ---- */
function facTouched(repaint){
  const d = state.fac.d; if(!d) return;
  if(repaint) facPaintForm();
  if(d.cv) cvFromGui(d.cv);
}
function facSet(key, value){
  const d = state.fac.d; if(!d) return;
  d.w[key] = value;
  facTouched(false);
}
/* Write one colour down, and update the row IN PLACE.

   `facTouched(false)` deliberately: repainting the form here is what used to
   close the OS colour picker on every drag (see facColour). The three things
   the row shows are set by hand instead, and `skip` leaves alone whichever box
   the user is currently typing in - writing a value back into the input you are
   mid-way through editing moves the caret to the end. */
function facWriteColour(key, hex, skip){
  const d = state.fac.d; if(!d) return;
  const n = parseInt(hex.slice(1), 16);
  d.w[key] = tt('factions.red_green_blue',{x:(n>>16)&255,x2:(n>>8)&255,x3:n&255});
  (d.colours = d.colours || {})[key] = hex;
  const sw = document.getElementById('fcs_' + key);
  const hx = document.getElementById('fch_' + key);
  const raw = document.getElementById('fcr_' + key);
  if(sw && skip !== 'swatch') sw.value = hex;
  if(hx && skip !== 'hex') hx.value = hex;
  if(raw) raw.textContent = d.w[key];
  facTouched(false);
}
function facSetColour(key, hex){ facWriteColour(key, hex, 'swatch'); }
/* Typed or pasted hex. An incomplete one (someone is still typing "#3a") is not
   an error and not a value - the record keeps what it had until the box holds a
   whole colour, so a half-typed code never lands in the file. */
function facSetHex(key, text){
  const hex = facHexFull(text);
  if(hex) facWriteColour(key, hex, 'hex');
}
function facSetLoc(value){
  const d = state.fac.d; if(!d) return;
  (d.locEdits = d.locEdits || {})[d.loc_tag] = value;
}
function facSetUnit(k, value){
  state.fac.d.w.horde_units[k] = value.trim();
  facTouched(true);
}
function facAddUnit(){
  const w = state.fac.d.w;
  (w.horde_units = w.horde_units || []).push('');
  facTouched(true);
}
function facDelUnit(k){
  state.fac.d.w.horde_units.splice(k, 1);
  facTouched(true);
}
// A group is all-or-nothing in the file, so it is all-or-nothing here: the boxes
// appear together, and the server puts each new line at its canonical place.
function facAddGroup(which){
  const d = state.fac.d, v = d.vocab || {};
  const keys = which === 'horde' ? (v.horde_keys || [])
    : ['intro_movie','victory_movie','defeat_movie','death_movie'];
  for(const k of keys) if(!d.w[k]) d.w[k] = which === 'horde' ? '0' : '';
  if(which === 'horde' && !(d.w.horde_units||[]).length) d.w.horde_units = [''];
  d.added = true;
  facTouched(true);
}

/* ---- the code view ---- */
async function facCvToggle(){
  const f = state.fac, d = f.d; if(!d) return;
  if(d.cv){ cvDrop(d.cv); d.cv = null; state.settings.code_view = false;
    api.post('/api/settings', {code_view:false}); facPaint(); return; }
  state.settings.code_view = true; api.post('/api/settings', {code_view:true});
  d.cv = cvCreate({kind:'factions', mod:f.mod, id:d.name, where:'data/' + f.file,
    edits:() => facEdits(),
    adopt:cv => { const s = state.fac.d;
      if(!cv.detail) return;
      s.w = cv.detail;
      // `base`, never `text`: with comment hiding on, `text` is the view with the
      // comment-only lines cut out of it, and saving that would delete every one
      // of them. `base` is the record's real bytes.
      s.raw = cv.edited ? cv.base : ''; },
    refreshGui:() => facPaintForm()});
  facPaint();
  await cvLoad(d.cv);
  if(state.fac.d !== d || !d.cv) return;
  facPaint();
}

/* ---- writing ---- */
function facEdits(){
  const d = state.fac.d, w = d.w, v = d.vocab || {};
  // Send a key when it has a value (unchanged ones cost nothing - the server
  // skips a key whose value has not moved) or when the record HAD it and the
  // box is now empty, which is how an optional line gets deleted. The repeat
  // key rides as `units`, which is what the shared serialiser calls it.
  const out = {units:(w.horde_units||[]).filter(Boolean)};
  for(const k of (v.order||[])){
    const val = w[k] || '';
    if(val !== '' || d.had.has(k)) out[k] = val;
  }
  return out;
}

function facBody(){
  const d = state.fac.d;
  const body = {mod:state.fac.mod, faction:d.name, action:'edit',
    edits:facEdits(), loc:d.locEdits || {}};
  if(d.raw) body.raw_block = d.raw;
  return body;
}

async function facSave(){
  const f = state.fac, d = f.d;
  if(f.busy) return;
  const body = facBody();
  f.busy = true;
  let plan;
  try{ plan = await api.post('/api/factions/plan', body); }
  finally{ f.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 6000); return; }
  const p = plan.plan || {};
  const lines = (p.changes || []).slice(0, 14);
  const found = (p.findings || []).map(x => '⚠ ' + x.message);
  const changes = `${lines.join('\n') || tt('common.no_visible_change')}${
    (p.changes || []).length > 14 ? tt('factions.and_more',{changes:p.changes.length - 14}) : ''}${
    found.length ? '\n\n' + found.slice(0, 4).join('\n') : ''}`;
  if(!confirm(tt('factions.confirm_write',{slot:d.slot,changes}))) return;
  f.busy = true;
  let res;
  try{ res = await api.post('/api/factions/apply', body); }
  finally{ f.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  if(typeof fauStale === 'function') fauStale();
  const keep = body.faction;
  // 17f: the roster is re-read either way, but only the mode may redraw the
  // page. On the campaign map this form is one div inside a panel, and
  // rebuilding `main` under it would take the map with it.
  try{ await facFetch(f.mod); }catch(e){ toast('✗ ' + errText(e), 6000); return; }
  if(state.mode === 'factions') renderFactions();
  if(keep) facOpen(keep);
}


/* ---- adding a faction, by cloning one that already works ------------------

   The roster tab spent its whole life explaining why it would NOT do this: a
   faction slot lives in thirteen files, and one that exists only in
   descr_sm_factions.txt is a mod that will not load. That is still true - the
   answer is to write all thirteen, which is what /api/factions/clone_plan does
   (see unittransfer/factionclone.py).

   The page's job here is narrow and it matters: this is the one action in the
   Factions tab that touches files the tab does not otherwise own - the EDU, the
   modeldb, descr_character - and it copies a folder of pictures besides. So
   nothing is written until the plan has been fetched and SHOWN, file by file,
   with the count of what each one would gain. The Create button stays disabled
   until that plan exists and is clean. */

/* Whether the engine's faction table has any room left. Asked in two places -
   the button and the dialog's own banner - so it is one answer, not two. A mod
   marked M2EX reports no limit at all, and 0 is never "full". */
function facFull(){
  const f = state.fac;
  return !!(f && f.limit && f.count >= f.limit);
}

function facCloneOpen(source){
  const f = state.fac;
  if(!f || !f.factions || !f.factions.length) return;
  const rows = f.factions.filter(r => r.slot !== 'slave');
  const donor = source || f.sel || (rows[0] && rows[0].name) || '';
  // 56 (M12): one row is the dialog as it always was; more rows are a batch,
  // planned one on top of the other and written as one job with one Undo
  f.clone = {source: fcSlotOf(donor), rows: [fcRowNew()], art: true, rename: true,
             plan: null, batch: null, busy: false, err: ''};
  facCloneRender();
  overlay.classList.add('open');
}

function fcRowNew(){ return {name: '', label: '', titles: {}, open: false}; }

/* The five text keys worth asking for at creation - factionclone.TITLE_KEYS.
   Blank leaves the donor's value, which is what a clone does everywhere else. */
const FC_TITLES = [
  ['leader', tt('factions.leader_title'), 'EMT_X_FACTION_LEADER_TITLE'],
  ['heir', tt('factions.heir_title'), 'EMT_X_FACTION_HEIR_TITLE'],
  ['former', tt('factions.former_leader_title'), 'EMT_X_FORMER_FACTION_LEADER_TITLE'],
  ['strength', tt('factions.strengths'), 'X_STRENGTH'],
  ['weakness', tt('factions.weaknesses'), 'X_WEAKNESS'],
];

/* The head line may carry a modifier after a comma (`egypt, spawned_on_event`)
   and everything else in a mod points at the part before it - the same rule as
   factions.py's slot_of, which is why this never sends a whole head line. */
function fcSlotOf(name){ return String(name || '').split(',')[0].trim(); }

/* The plan and the Create button, without rebuilding the fields.

   Redrawing the whole dialog every time a plan lands takes the caret out of the
   box the person is still typing in - they type `arnor`, the preview returns
   280ms later, and the next letter goes nowhere. So the debounced preview
   repaints only the two things it actually changes. */
function facClonePaint(){
  const c = state.fac && state.fac.clone;
  if(!c) return;
  const host = document.getElementById('fcPlan');
  if(!host) return facCloneRender();          // dialog not up: draw it whole
  host.innerHTML = facClonePlanHtml();
  const go = document.querySelector('.foot .primary');
  if(go) go.disabled = !(facCloneReady() && !c.busy);
  const note = document.getElementById('fcNote');
  if(note) note.textContent = c.busy ? tt('common.working_out_what_would_change') : '';
}

function facCloneRender(){
  const f = state.fac, c = f.clone;
  if(!c) return;
  // whatever was focused has to come back after innerHTML replaces it
  const live = document.activeElement || {};
  const keep = (live.id && /^fc(Name|Label|T)/.test(live.id)) ? live.id : '';
  const at = keep ? live.selectionStart : 0;
  const rows = f.factions.filter(r => r.slot !== 'slave');
  const p = c.plan || null;
  const full = facFull();
  document.getElementById('modal').innerHTML = `
    <h2>${tt('factions.add_a_faction_2')} <span class="pill">${esc(f.mod || state.src)}</span></h2>
    <div class="mbody" style="padding:14px 16px">
      <div class="count fcintro">
        ${tt('factions.a_faction_is_added_by_copying')}
      </div>
      ${full ? `<div class="w-warn fcmsg">${tt('factions.this_mod_already_uses_all_of',{limit:f.limit})}</div>` : ''}
      <div class="fcgrid">
        <label class="v3f"><span>${tt('factions.copy_from')}</span>
          <select onchange="facCloneSet('source', this.value)">
            ${rows.map(r => `<option value="${q1(esc(r.slot))}"${
              r.slot === c.source ? ' selected' : ''
            }>${esc(r.label)}</option>`).join('')}
          </select></label>
        <span></span><span></span>
      </div>
      ${c.rows.map((r, i) => `<div class="fcgrid fcrowin">
        <label class="v3f"><span>${c.rows.length > 1 ? tt('factions.new_faction',{x:i + 1}) : tt('factions.new_faction_slot')}</span>
          <input type="text" id="fcName${i}" value="${q1(esc(r.name))}"
            placeholder="${ttA('factions.e_g_gondor_south')}" spellcheck="false"
            oninput="facCloneSet('name', this.value, ${i})"></label>
        <label class="v3f"><span>${tt('factions.shown_name_optional')}</span>
          <input type="text" id="fcLabel${i}" value="${q1(esc(r.label))}"
            placeholder="${ttA('factions.what_the_game_calls_it')}"
            oninput="facCloneSet('label', this.value, ${i})"></label>
        <span class="fcrowbtns">
          <button onclick="facCloneFold(${i})" class="${r.open ? 'on' : ''}"
            title="${ttA('factions.leader_and_heir_titles_strengths_and')}">${tt('factions.titles',{x:Object.values(r.titles).some(v => v) ? ' ●' : ''})}</button>
          ${c.rows.length > 1 ? `<button onclick="facCloneDrop(${i})" title="${ttA('factions.take_this_one_out')}">✕</button>` : ''}
        </span>
        ${r.open ? `<div class="fctitles">${FC_TITLES.map(([k, lab, key]) =>
          `<label class="v3f"><span>${lab} <code>${esc(key.replace('X', (r.name || 'slot').toUpperCase()))}</code></span>
            <input type="text" id="fcT${i}_${k}" value="${q1(esc(r.titles[k] || ''))}"
              placeholder="${ttA('factions.blank_keeps_the_donors')}" oninput="facCloneTitle(${i}, '${k}', this.value)"></label>`
        ).join('')}</div>` : ''}
      </div>`).join('')}
      <button class="fcmore" onclick="facCloneRow()" title="${ttA('factions.add_several_factions_from_the_same')}">${tt('factions.another_faction')}</button>
      <div class="count fcintro">
        ${tt('factions.the_slot_is_what_every_other')}
      </div>
      <label class="fcart"><input type="checkbox"${c.art ? ' checked' : ''}
        onchange="facCloneSet('art', this.checked)">
        <span>${tt('factions.copy_the_art_too_symbols_banners')}</span></label>
      <label class="fcart"><input type="checkbox"${c.rename ? ' checked' : ''}
        onchange="facCloneSet('rename', this.checked)">
        <span>${tt('factions.where_the_donors_shown_name_stands')}</span></label>
      <div id="fcPlan">${facClonePlanHtml()}</div>
    </div>
    <div class="foot">
      <span class="count" id="fcNote">${c.busy ? tt('common.working_out_what_would_change') : ''}</span>
      <button onclick="facCloneClose()">${tt('common.cancel')}</button>
      <button class="primary"${(facCloneReady() && !c.busy) ? '' : ' disabled'}
        onclick="facCloneApply()">${c.rows.length > 1 ? tt('factions.create_factions',{rows_n:c.rows.length}) : tt('factions.create_faction')}</button>
    </div>`;
  if(keep){
    const box = document.getElementById(keep);
    if(box){ box.focus(); box.setSelectionRange(at, at); }
  }
}

function facCloneReady(){
  const c = state.fac && state.fac.clone;
  if(!c) return false;
  return c.rows.length > 1 ? !!(c.batch && c.batch.ok) : !!(c.plan && c.plan.ok);
}
function facCloneRow(){
  const c = state.fac.clone;
  if(!c) return;
  c.rows.push(fcRowNew());
  facCloneRender();
  const box = document.getElementById('fcName' + (c.rows.length - 1));
  if(box) box.focus();
  facCloneSoon(0);
}
function facCloneDrop(i){
  const c = state.fac.clone;
  if(!c || c.rows.length < 2) return;
  c.rows.splice(i, 1);
  facCloneRender();
  facCloneSoon(0);
}
function facCloneFold(i){
  const c = state.fac.clone;
  if(!c) return;
  c.rows[i].open = !c.rows[i].open;
  facCloneRender();
}
function facCloneTitle(i, k, v){
  const c = state.fac.clone;
  if(!c) return;
  c.rows[i].titles[k] = v;
  facCloneSoon(280);
}
function facCloneSoon(ms){
  clearTimeout(state.fac._fcT);
  state.fac._fcT = setTimeout(facClonePreview, ms);
}

/* The plan, file by file. A file that would gain nothing is shown greyed with
   the reason rather than hidden: "descr_character.txt - sicily is not named in
   it" is a fact about the mod worth reading before you write, not noise. */
function facClonePlanHtml(){
  const c = state.fac.clone;
  if(c.err) return `<div class="w-warn fcmsg">${esc(c.err)}</div>`;
  if(c.rows.length > 1) return facCloneBatchHtml(c.batch);
  return facClonePlanBody(c.plan);
}

/* A batch: one line per new faction, each opening onto its own plan, and the
   files the whole job writes - each once, as the last row leaves it. */
function facCloneBatchHtml(b){
  if(!b) return `<div class="count fcintro">${tt('factions.name_the_new_factions_to_see')}</div>`;
  const rows = b.rows || [];
  return `<div class="fcplan">
    <div class="k">${tt('factions.what_would_be_written_factions_file',{rows_n:rows.length,n:(b.files || []).length,asset_files:b.asset_files ? tt('factions.art_file_s',{asset_files:b.asset_files}) : ''})}</div>
    ${(b.errors || []).length ? `<div class="w-warn fcmsg">${b.errors.map(esc).join('<br>')}</div>` : ''}
    ${rows.map(r => `<details class="fcbatch"><summary>
        <span class="${r.ok ? 'ok' : 'bad'}">${r.ok ? '✓' : '✗'}</span>
        <b>${esc(r.new || 'unnamed')}</b> <span class="count">${tt('factions.from_file_s',{source:esc(r.source),n:(r.files || []).filter(x => x.written).length,asset_files:r.asset_files ? tt('factions.art_file_s',{asset_files:r.asset_files}) : '',art_gaps:(r.art_gaps || []).length ? tt('factions.art_place_s_empty',{art_gaps_n:r.art_gaps.length}) : ''})}</span>
      </summary>${facClonePlanBody(r)}</details>`).join('')}
  </div>`;
}

function facClonePlanBody(p){
  if(!p) return `<div class="count fcintro">${tt('factions.name_the_new_faction_to_see')}</div>`;
  if((p.errors || []).length)
    return `<div class="w-warn fcmsg">${p.errors.map(esc).join('<br>')}</div>`;
  const files = p.files || [];
  return `<div class="fcplan">
    <div class="k">${tt('factions.what_would_be_written_file_s',{n:files.filter(x => x.written).length,x:p.asset_files ? tt('factions.art_file_s_mb',{asset_files:p.asset_files,asset_bytes:(p.asset_bytes / 1048576).toFixed(1)}) : '',art_gaps:(p.art_gaps || []).length
          ? tt('factions.art_place_s_empty',{art_gaps_n:p.art_gaps.length}) : ''})}</div>
    ${files.map(x => `<div class="fcrow${x.written ? '' : ' off'}">
      <span class="fcc">${x.written ? '+' + x.count : '-'}</span>
      <span class="fcn">${esc(x.label)}
        <span class="fcf">${esc(x.rel)}</span></span>
      <span class="fcw count">${esc(x.written ? (x.note || '') : (x.skipped || ''))}</span>
    </div>`).join('')}
    ${(p.review || []).length ? `<div class="fcrow fcrev">
      <span class="fcc">-</span>
      ${tt('factions.left_for_you_to_decide_the',{x:p.review.map(r => esc(r.rel) + ' (' + r.hits + ')').join(', ')})}</div>` : ''}
    ${(p.art_gaps || []).map(g => `<div class="fcrow fcgap" data-why="${esc(g.reason)}">
      <span class="fcc">0</span>
      <span class="fcn">${esc(g.label)}
        <span class="fcf">${esc(g.rel)}</span></span>
      <span class="fcw count">${esc(g.what)}${
        g.note ? `<span class="fcgw">${esc(g.note)}</span>` : ''}</span>
    </div>`).join('')}
    ${(p.warnings || []).map(w => `<div class="w-warn fcmsg">${esc(w)}</div>`).join('')}
    ${(p.notes || []).map(n => `<div class="fcmsg count">${esc(n)}</div>`).join('')}
  </div>`;
}

function facCloneClose(){ if(state.fac) state.fac.clone = null; closeModal(); }

function facCloneSet(key, value, i){
  const c = state.fac.clone;
  if(!c) return;
  // the slot is typed as it will be written: one lower-case word
  if(key === 'name') value = String(value).toLowerCase().replace(/[^a-z0-9_]+/g, '_');
  if(key === 'name' || key === 'label') c.rows[i || 0][key] = value;
  else c[key] = value;
  facCloneRender();
  facCloneSoon((key === 'art' || key === 'rename' || key === 'source') ? 0 : 280);
}

async function facClonePreview(){
  const c = state.fac && state.fac.clone;
  if(!c) return;
  if(!c.rows.some(r => r.name)){ c.plan = null; c.batch = null; c.err = ''; facClonePaint(); return; }
  c.busy = true; c.err = '';
  const note = document.getElementById('fcNote');
  if(note) note.textContent = tt('common.working_out_what_would_change');
  let r;
  try{ r = await api.post('/api/factions/clone_plan', facCloneBody()); }
  catch(e){ r = {error: String((e && e.message) || e)}; }
  finally{ c.busy = false; }
  if(!state.fac || state.fac.clone !== c) return;   // the dialog moved on
  c.plan = r.plan || null;
  c.batch = r.batch || null;
  // an error the plan already carries is drawn in place; anything else is ours
  const drawn = (r.plan && (r.plan.errors || []).length) || (r.batch && (r.batch.errors || []).length);
  c.err = (r.error && !drawn) ? r.error : '';
  facClonePaint();
}

function facCloneBody(){
  const c = state.fac.clone;
  const titles = r => Object.fromEntries(Object.entries(r.titles).filter(([, v]) => v && v.trim()));
  if(c.rows.length > 1)
    return {mod: state.src, source: c.source, art: !!c.art, rename: !!c.rename,
            rows: c.rows.map(r => ({new: r.name, label: r.label, titles: titles(r)}))};
  const r = c.rows[0];
  return {mod: state.src, source: c.source, new: r.name, label: r.label,
          titles: titles(r), art: !!c.art, rename: !!c.rename};
}

async function facCloneApply(){
  const f = state.fac, c = f.clone;
  if(!c || c.busy || !facCloneReady()) return;
  if(c.rows.length > 1) return facCloneApplyMany();
  const p = c.plan, name = c.rows[0].name;
  const files = (p.files || []).filter(x => x.written);
  if(!confirm(tt('factions.confirm_add_one',{name,source:c.source,
    files:files.map(x => `  ${x.rel}  +${x.count}`).join('\n'),
    art:p.asset_files ? tt('factions.art_file_s_copied_and_renamed',{asset_files:p.asset_files}) : '',
    // the review files live in `review`, not in the note, so this dialog names
    // them itself - it has no row to draw them in the way the plan pane does
    review:(p.review || []).length ? tt('factions.confirm_review',
      {mentions:p.review.map(r => tt('factions.mention_s',{rel:r.rel,hits:r.hits})).join('\n')}) : '',
    // 42: the art the clone will NOT get, said here rather than found in the
    // game. A donor with nothing in a folder cannot fill it, so this is the
    // last point at which picking a different donor is still a choice.
    gaps:(p.art_gaps || []).length
      ? tt('factions.confirm_art_gaps',{art_gaps_n:p.art_gaps.length,
          gaps:p.art_gaps.map(g => `  ${g.label}  (${g.rel})\n    ${g.what}`).join('\n')})
      : '',
    notes:(p.notes || []).join('\n\n')}))) return;
  c.busy = true;
  facCloneRender();
  let res;
  try{ res = await api.post('/api/factions/clone_apply', facCloneBody()); }
  finally{ c.busy = false; }
  if(res.error){ c.err = res.error; facCloneRender(); toast('✗ ' + res.error, 6000); return; }
  activity(tt('factions.added_faction'), tt('factions.cloned_from_in',{name,source:c.source,src:state.src}));
  const keep = name;
  f.clone = null;
  closeModal();
  toast(tt('factions.added_one_toast',{keep,files_n:res.files.length,asset_files:res.asset_files}), 5000);
  if(typeof fauStale === 'function') fauStale();
  // 21: the audit offers this dialog from the campaign map's faction screen too,
  // and there `main` is the map - only the mode may redraw the page (17f's rule)
  if(state.mode === 'factions'){ await loadFactions(); facOpen(keep); return; }
  try{ await facFetch(f.mod); }catch(e){}
  if(state.mode === 'campmap' && typeof cjPickFaction === 'function') cjPickFaction(keep);
}

async function facCloneApplyMany(){
  const f = state.fac, c = f.clone, b = c.batch;
  const names = c.rows.map(r => r.name);
  if(!confirm(tt('factions.confirm_add_many',{names_n:names.length,source:c.source,
    names:names.join('\n  '),n:(b.files || []).length,
    art:b.asset_files ? tt('factions.and_art_file_s_copied_and',{asset_files:b.asset_files}) : ''}))) return;
  c.busy = true;
  facCloneRender();
  let res;
  try{ res = await api.post('/api/factions/clone_apply', facCloneBody()); }
  finally{ c.busy = false; }
  if(res.error){ c.err = res.error; facCloneRender(); toast('✗ ' + res.error, 6000); return; }
  activity(tt('factions.added_factions'), tt('factions.cloned_from_in_2',{names:names.join(', '),source:c.source,src:state.src}));
  f.clone = null;
  closeModal();
  toast(tt('factions.added_many_toast',{names_n:names.length,files_n:res.files.length,asset_files:res.asset_files}), 6000);
  if(typeof fauStale === 'function') fauStale();
  if(state.mode === 'factions'){ await loadFactions(); facOpen(names[0]); return; }
  try{ await facFetch(f.mod); }catch(e){}
}
