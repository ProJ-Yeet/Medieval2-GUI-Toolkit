/* factions.js — Factions mode: descr_sm_factions.txt, the faction roster

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html — there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= FACTIONS MODE =======================
   What a faction IS: its culture and religion, the two colours it paints the
   campaign map with, the strat models it puts on it, what it may and may not do,
   and — for the few that have one — its horde.

   Four things about this screen that the file decided:

     * THE LOCALISED NAME MATTERS MORE HERE THAN ANYWHERE. Mods reuse vanilla
       slots wholesale, so DaC's `sicily` is the Kingdom of Gondor and its
       `turks` are somebody else again. A list of slots would be a list of the
       wrong countries; every row leads with the real name.
     * THE SLOT CANNOT BE RENAMED. descr_strat, every unit's ownership line,
       every `requires factions { … }` clause, descr_names and its own
       expanded.txt entry all point at it. The head line's modifier after the
       comma (`faction egypt, spawned_on_event`) is shown but not edited here.
     * ADD BY CLONING, NEVER DELETE. A faction lives in twelve files at once,
       so one that exists only in this file is a mod that will not load — which
       is an argument for writing all twelve, not for refusing. ＋ Add a faction
       copies a working faction into every one of them (factionclone.py).
       Deleting stays out: a clone copies the donor's answer, and a delete would
       have to invent one for every line that names the slot.
     * A MISSING PICTURE IS NOT A FAULT. `symbol` and `rebel_symbol` are .CAS 3D
       models, and not one of the 90 real factions measured ships its
       `loading_logo` unpacked — they are all inside the game's .pack archives.
       So the paths are shown and a found one is marked; an unfound one is not
       called missing.

   The colours ARE ours to show, and they are the only genuinely visual thing in
   the file: `primary_colour red 55, green 75, blue 48` gets a swatch and a picker.

   THE PAGE NEVER PARSES A GAME FILE: /api/factions, /api/faction,
   /api/factions/plan|apply and /api/factions/clone_plan|clone_apply do all of
   it — including working out which twelve files a new faction would change. */

async function loadFactions(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s factions…</div>';
  let r;
  try{ r = await api.get('/api/factions?mod=' + enc(mod)); }
  catch(e){ if(stale('factions', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read the faction roster.<br>
      <span class="count">${esc(errText(e))}</span><br><br>
      <button class="primary" onclick="loadFactions()">Retry</button></div>`; return; }
  if(stale('factions', mod)) return;
  state.fac = Object.assign({sel:'', d:null, busy:false}, r);
  undoReset();
  renderFactions();
}

function renderFactions(){
  const f = state.fac;
  if(!f){ loadFactions(); return; }
  const strip = minorTabsHtml('', 'data/descr_sm_factions.txt');
  if(f.error || !f.exists){
    main.innerHTML = strip + `<div class="empty">${esc(f.error || 'No faction roster.')}<br>
      <span class="count">It lives in data/descr_sm_factions.txt</span></div>`;
    return;
  }
  const rows = facRows();
  count.textContent = `${rows.length}/${f.count}`;
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('factions', f.finding_list, 'facOpen')}
      <div class="trnote">${f.limit ? `${f.count}/${f.limit} faction slots used`
        : `${f.count} faction slots — this mod is marked <b>M2EX</b>, so the
           engine's ${VANILLA_FACTION_LIMIT} is not its ceiling`}
        ${f.can_clone ? `<button class="fcadd" onclick="facCloneOpen()"
          ${facFull() ? 'disabled' : ''} title="${facFull()
            ? 'Every faction slot the engine has is already used'
            : 'Add a faction by copying one that already works, into all twelve files that name a slot'}"
          >＋ Add a faction</button>` : ''}</div>
      <div class="trrows">${rows.map(facRowHtml).join('')
        || '<div class="count" style="padding:8px">No faction matches.</div>'}</div>
    </div>
    <div class="trmain" id="facMain">${facDetailHtml()}</div>
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
      <span class="sub">${esc(r.culture||'no culture')} · ${esc(r.religion||'no religion')}${
        r.horde?` · horde of ${r.horde}`:''}${
        r.special?` · ${esc(r.special)}`:''}${
        r.modifier?` · ${esc(r.modifier)}`:''}${
        r.findings?` <span class="w-warn">· ${r.findings}⚠</span>`:''}</span>
    </span>
  </button>`;
}

async function facOpen(name){
  activity('opened faction', `${name} in ${state.src}`);
  const f = state.fac;
  f.sel = name; f.d = null;
  renderFactions();
  let d;
  try{ d = await api.get(`/api/faction?mod=${enc(f.mod)}&name=${enc(name)}`); }
  catch(e){ d = {error:''+e}; }
  if(state.mode !== 'factions' || state.fac !== f || f.sel !== name) return;
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
  const d = state.fac.d;
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
  if(!f.sel) return `<div class="empty">Pick a faction on the left.<br>
    <span class="count">${f.count} faction${f.count===1?'':'s'} in data/${esc(f.file)}</span>
    <div class="trnote" style="max-width:600px;margin:14px auto;text-align:left">${
      esc(f.refused)}</div></div>`;
  if(!d) return '<div class="empty">Reading the faction…</div>';
  if(d.error) return `<div class="empty"><span class="w-bad">✗ ${esc(d.error)}</span></div>`;
  return `<div class="trbar">
      <div><b>${esc(d.label)}</b>
        <span class="count">${esc(d.faction.culture||'')}${
          d.modifier?' · '+esc(d.modifier):''}</span></div>
      <span class="sp"></span>
      <button class="${d.cv?'on':''}" title="Show this faction exactly as
descr_sm_factions.txt stores it, beside the form."
        onclick="facCvToggle()">&lt;/&gt; Code view</button>
      <button class="primary" onclick="facSave()">Save</button>
    </div>
    <div id="facGui">
      ${facFindingsHtml(d)}
      ${facFormHtml(d)}
    </div>
    ${d.cv ? `<div id="facCodeCol" style="padding-top:12px">${cvHtml(d.cv)}</div>` : ''}`;
}

function facFindingsHtml(d){
  const out = (d.findings||[]).map(f =>
    `<div class="trfind w-warn">line ${f.line}: ${esc(f.message)}</div>`);
  if((d.missing_loc||[]).length) out.push(`<div class="trfind w-warn">
    There is no <code>{${esc(d.loc_tag)}}</code> entry in ${esc(d.loc_file)}, so this
    faction shows its slot name in game. Type its name beside the slot below, or
    save and the key is created with the slot as placeholder text.</div>`);
  return out.join('');
}

/* ---- the form ---- */
function facFormHtml(d){
  const w = d.w, v = d.vocab || {};
  const shownName = d.locEdits[d.loc_tag] !== undefined
    ? d.locEdits[d.loc_tag] : ((d.loc||{})[d.loc_tag] || '');
  return `<section class="trsec">
    <div class="trsechead">The faction
      <span class="count">The line order here is what all 90 real factions
        measured write, so an added line goes to its place in it</span></div>
    <div class="trgrid">
      <label class="lbl" data-label="name">Slot</label>
      <div class="trkey">
        <input data-label="name" value="${esc(d.slot)}" disabled
          title="The faction slot. descr_strat, every unit's ownership line and
every 'requires factions' clause point at it, so it is not renamed here.">
        <input class="trtext" value="${esc(shownName)}"
          placeholder="${((d.loc||{})[d.loc_tag] === undefined)
            ? 'not in ' + esc(d.loc_file) + ' yet' : 'the faction’s name in game'}"
          title="What the player reads. Saved into data/${esc(d.loc_file)}."
          oninput="facSetLoc(this.value)">
      </div>
      ${d.modifier ? `<label class="lbl">Head modifier</label>
        <div><input value="${esc(d.modifier)}" disabled>
        <div class="trhint count">Carried on the <code>faction</code> line itself;
          edited in the code view</div></div>` : ''}
      ${facPick(d, 'culture', 'Culture', v.cultures)}
      ${facPick(d, 'religion', 'Religion', v.religions)}
      ${facColour(d, 'primary_colour', 'Primary colour')}
      ${facColour(d, 'secondary_colour', 'Secondary colour')}
      ${facPick(d, 'special_faction_type', 'Special type', v.special_types, true)}
    </div>
  </section>
  <section class="trsec">
    <div class="trsechead">Art and banners
      <span class="count">Symbol lines name .CAS strat MODELS, not textures. A
        loading logo normally lives inside the game's .pack archives, so "not
        found" here is not "missing"</span></div>
    ${facPictures(d)}
    <div class="trgrid">
      ${(v.art_keys||[]).map(k => facArt(d, k)).join('')}
      ${facBox(d, 'standard_index', 'Banner index')}
      ${facBox(d, 'logo_index', 'Logo index', v.logo_indexes)}
      ${facBox(d, 'small_logo_index', 'Small logo index', v.small_logo_indexes)}
      ${facBox(d, 'triumph_value', 'Triumph value')}
    </div>
  </section>
  <section class="trsec">
    <div class="trsechead">What it can do</div>
    <div class="trgrid">
      ${(v.yes_no||[]).map(k => facYesNo(d, k)).join('')}
      ${facPick(d, 'has_family_tree', 'has_family_tree', v.family_tree)}
    </div>
    <div class="trhint count">has_family_tree is not a yes/no: 24 of the 90 real
      factions measured say <code>teutonic</code>, and a checkbox would have
      written <code>no</code> over every one of them.</div>
  </section>
  ${facMovies(d)}
  ${facHorde(d)}`;
}

const facHas = (d, k) => (d.w[k] || '') !== '';

function facBox(d, key, label, list){
  const id = 'facdl-' + key;
  return `<label class="lbl" data-label="${key}">${esc(label)}</label>
    <div><input data-label="${key}" value="${esc(d.w[key]||'')}"
      ${list&&list.length?`list="${id}"`:''}
      oninput="facSet('${key}',this.value.trim())">
    ${list&&list.length?`<datalist id="${id}">${list.map(x =>
      `<option value="${esc(x)}">`).join('')}</datalist>`:''}</div>`;
}

function facPick(d, key, label, options, optional){
  const cur = d.w[key] || '', opts = options || [];
  return `<label class="lbl" data-label="${key}">${esc(label)}</label>
    <div><select data-label="${key}" onchange="facSet('${key}',this.value)">
      ${optional?`<option value=""${cur?'':' selected'}>None</option>`:''}
      ${opts.map(o => `<option value="${esc(o)}"${o===cur?' selected':''}>${esc(o)}</option>`).join('')}
      ${cur && !opts.includes(cur)
        ? `<option value="${esc(cur)}" selected>${esc(cur)} (not in this mod)</option>` : ''}
    </select></div>`;
}

function facYesNo(d, key){
  const cur = d.w[key] || '';
  if(!facHas(d, key) && !d.had.has(key)) return '';
  return `<label class="lbl" data-label="${key}">${esc(key)}</label>
    <div><select data-label="${key}" onchange="facSet('${key}',this.value)">
      ${['yes','no'].map(o => `<option value="${esc(o)}"${o===cur?' selected':''}>${esc(o)}</option>`).join('')}
      ${cur && cur!=='yes' && cur!=='no'
        ? `<option value="${esc(cur)}" selected>${esc(cur)} (not yes or no)</option>` : ''}
    </select></div>`;
}

function facColour(d, key, label){
  const hex = (d.colours||{})[key] || '#000000';
  return `<label class="lbl" data-label="${key}">${esc(label)}</label>
    <div class="faccol">
      <input type="color" value="${esc(hex)}"
        oninput="facSetColour('${key}',this.value)">
      <input value="${esc(d.w[key]||'')}" class="faccolt"
        oninput="facSet('${key}',this.value.trim())">
    </div>`;
}

/* The faction's pictures. The roster names none of them (see factions.py), so
   they are found where the game itself looks — and a mod that keeps its art in
   a .pack archive simply has none to show, which is not a fault. */
function facPictures(d){
  const pics = d.pictures || [];
  if(!pics.length) return `<div class="trhint count" style="margin-bottom:8px">
    No unpacked pictures for <code>${esc(d.slot)}</code>. Normal: most mods keep
    faction art inside the game's <code>.pack</code> archives.</div>`;
  return `<div class="facpics">${pics.map(p => {
    const url = `/icon?mod=${enc(state.fac.mod)}&kind=faction&rel=${enc(p.rel)}`;
    return `<figure>
      <div class="icowrap"><img loading="lazy" onerror="iconRetry(this)"
        title="Replace this picture" onclick="imgPick('${q1(esc(url))}','facPaint')"
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
        ? '✓ found in this mod'
        : 'Not unpacked here. Normally that means it is inside a .pack archive'}</div>
    </div>`;
}

function facMovies(d){
  const keys = ['intro_movie','victory_movie','defeat_movie','death_movie'];
  const any = keys.some(k => d.had.has(k) || facHas(d, k));
  if(!any) return `<section class="trsec">
    <div class="trsechead">Movies <span class="count">This faction has none, and
      63% of the real factions measured do</span></div>
    <button class="trgadd" onclick="facAddGroup('movies')">＋ Add the four movie lines</button>
  </section>`;
  return `<section class="trsec">
    <div class="trsechead">Movies <span class="count">.bik files under data/</span></div>
    <div class="trgrid">${keys.map(k => facBox(d, k, k)).join('')}</div>
  </section>`;
}

function facHorde(d){
  const v = d.vocab || {}, keys = v.horde_keys || [];
  const any = keys.some(k => d.had.has(k) || facHas(d, k));
  if(!any) return `<section class="trsec">
    <div class="trsechead">Horde <span class="count">This faction has none</span></div>
    <button class="trgadd" onclick="facAddGroup('horde')">＋ Make this a horde faction</button>
  </section>`;
  const units = d.w.horde_units || [];
  return `<section class="trsec">
    <div class="trsechead">Horde
      <span class="count">The eight settings only mean anything together</span></div>
    <div class="trgrid">${keys.map(k => facBox(d, k, k)).join('')}</div>
    <div class="treffects">
      <div class="trsechead" style="margin:8px 0 0">Horde units
        <span class="count">${units.length}: what it spawns when it loses its
          last settlement</span></div>
      ${units.map((u,k)=>`<div class="treff" data-label="horde_unit#${k+1}">
        <input class="trattr" value="${esc(u)}" list="facUnits" placeholder="unit type"
          oninput="facSetUnit(${k},this.value)">
        <span class="count">${esc(facUnitLabel(d, u))}</span>
        <button class="trgdel" onclick="facDelUnit(${k})">✕</button>
      </div>`).join('')}
      <datalist id="facUnits">${(v.units||[]).map(u =>
        `<option value="${esc(u.type)}">${esc(u.label)}</option>`).join('')}</datalist>
      <button class="trgadd" onclick="facAddUnit()">＋ Add horde unit</button>
    </div>
  </section>`;
}

function facUnitLabel(d, type){
  if(!type) return '';
  const hit = ((d.vocab||{}).units||[]).find(u => u.type === type);
  return hit ? hit.label : '✗ not a unit in this mod';
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
function facSetColour(key, hex){
  const d = state.fac.d; if(!d) return;
  const n = parseInt(hex.slice(1), 16);
  d.w[key] = `red ${(n>>16)&255}, green ${(n>>8)&255}, blue ${n&255}`;
  d.colours[key] = hex;
  facTouched(true);
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
  // Send a key when it has a value (unchanged ones cost nothing — the server
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
  if(!confirm(`Write: save ${d.slot}?\n\n` + (lines.join('\n') || 'no visible change')
    + ((p.changes || []).length > 14 ? `\n…and ${p.changes.length - 14} more` : '')
    + (found.length ? '\n\n' + found.slice(0, 4).join('\n') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  f.busy = true;
  let res;
  try{ res = await api.post('/api/factions/apply', body); }
  finally{ f.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 6000); return; }
  toast('Saved. 🕑 Log can undo it.');
  const keep = body.faction;
  await loadFactions();
  if(keep) facOpen(keep);
}


/* ---- adding a faction, by cloning one that already works ------------------

   The roster tab spent its whole life explaining why it would NOT do this: a
   faction slot lives in twelve files, and one that exists only in
   descr_sm_factions.txt is a mod that will not load. That is still true — the
   answer is to write all twelve, which is what /api/factions/clone_plan does
   (see unittransfer/factionclone.py).

   The page's job here is narrow and it matters: this is the one action in the
   Factions tab that touches files the tab does not otherwise own — the EDU, the
   modeldb, descr_character — and it copies a folder of pictures besides. So
   nothing is written until the plan has been fetched and SHOWN, file by file,
   with the count of what each one would gain. The Create button stays disabled
   until that plan exists and is clean. */

/* Whether the engine's faction table has any room left. Asked in two places —
   the button and the dialog's own banner — so it is one answer, not two. A mod
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
  f.clone = {source: fcSlotOf(donor), name: '', label: '', art: true,
             plan: null, busy: false, err: ''};
  facCloneRender();
  overlay.classList.add('open');
}

/* The head line may carry a modifier after a comma (`egypt, spawned_on_event`)
   and everything else in a mod points at the part before it — the same rule as
   factions.py's slot_of, which is why this never sends a whole head line. */
function fcSlotOf(name){ return String(name || '').split(',')[0].trim(); }

/* The plan and the Create button, without rebuilding the fields.

   Redrawing the whole dialog every time a plan lands takes the caret out of the
   box the person is still typing in — they type `arnor`, the preview returns
   280ms later, and the next letter goes nowhere. So the debounced preview
   repaints only the two things it actually changes. */
function facClonePaint(){
  const c = state.fac && state.fac.clone;
  if(!c) return;
  const host = document.getElementById('fcPlan');
  if(!host) return facCloneRender();          // dialog not up: draw it whole
  host.innerHTML = facClonePlanHtml();
  const go = document.querySelector('.foot .primary');
  if(go) go.disabled = !(c.plan && c.plan.ok && !c.busy);
  const note = document.getElementById('fcNote');
  if(note) note.textContent = c.busy ? 'Working out what would change…' : '';
}

function facCloneRender(){
  const f = state.fac, c = f.clone;
  if(!c) return;
  // whatever was focused has to come back after innerHTML replaces it
  const live = document.activeElement || {};
  const keep = (live.id === 'fcName' || live.id === 'fcLabel') ? live.id : '';
  const at = keep ? live.selectionStart : 0;
  const rows = f.factions.filter(r => r.slot !== 'slave');
  const p = c.plan || null;
  const full = facFull();
  document.getElementById('modal').innerHTML = `
    <h2>Add a faction <span class="pill">${esc(f.mod || state.src)}</span></h2>
    <div class="mbody" style="padding:14px 16px">
      <div class="count fcintro">
        A faction is added by <b>copying one that already works</b> — into all
        twelve files that name a faction slot, plus its symbols, banners and unit
        cards. The clone starts identical to the faction it copies; change what
        you want afterwards in this tab and the editors beside it.
      </div>
      ${full ? `<div class="w-warn fcmsg">This mod already uses all ${f.limit}
        of the engine's faction slots, so nothing can be added until one goes.</div>` : ''}
      <div class="fcgrid">
        <label class="v3f"><span>Copy from</span>
          <select onchange="facCloneSet('source', this.value)">
            ${rows.map(r => `<option value="${q1(esc(r.slot))}"${
              r.slot === c.source ? ' selected' : ''
            }>${esc(r.label)}</option>`).join('')}
          </select></label>
        <label class="v3f"><span>New faction slot</span>
          <input type="text" id="fcName" value="${q1(esc(c.name))}"
            placeholder="e.g. gondor_south" spellcheck="false"
            oninput="facCloneSet('name', this.value)"></label>
        <label class="v3f"><span>Shown name <span class="count">(optional)</span></span>
          <input type="text" id="fcLabel" value="${q1(esc(c.label))}"
            placeholder="what the game calls it"
            oninput="facCloneSet('label', this.value)"></label>
      </div>
      <div class="count fcintro">
        The slot is what every other file points at, so it has to be one bare
        word: lower case, digits and underscores. It cannot be renamed later
        without orphaning every line that names it. The shown name is the only
        text filled in for you — the faction's other thirty text entries stay
        the donor's until you edit them.
      </div>
      <label class="fcart"><input type="checkbox"${c.art ? ' checked' : ''}
        onchange="facCloneSet('art', this.checked)">
        <span>Copy the art too — symbols, banners, captain cards and the unit
        card folders, each renamed for the new slot</span></label>
      <div id="fcPlan">${facClonePlanHtml()}</div>
    </div>
    <div class="foot">
      <span class="count" id="fcNote">${c.busy ? 'Working out what would change…' : ''}</span>
      <button onclick="facCloneClose()">Cancel</button>
      <button class="primary"${(p && p.ok && !c.busy) ? '' : ' disabled'}
        onclick="facCloneApply()">Create faction</button>
    </div>`;
  if(keep){
    const box = document.getElementById(keep);
    if(box){ box.focus(); box.setSelectionRange(at, at); }
  }
}

/* The plan, file by file. A file that would gain nothing is shown greyed with
   the reason rather than hidden: "descr_character.txt — sicily is not named in
   it" is a fact about the mod worth reading before you write, not noise. */
function facClonePlanHtml(){
  const c = state.fac.clone, p = c.plan;
  if(c.err) return `<div class="w-warn fcmsg">${esc(c.err)}</div>`;
  if(!p) return `<div class="count fcintro">Name the new faction to see exactly
    which files would change, and by how much.</div>`;
  if((p.errors || []).length)
    return `<div class="w-warn fcmsg">${p.errors.map(esc).join('<br>')}</div>`;
  const files = p.files || [];
  return `<div class="fcplan">
    <div class="k">What would be written
      <span class="count">${files.filter(x => x.written).length} file(s)${
        p.asset_files ? ` · ${p.asset_files} art file(s), ${
          (p.asset_bytes / 1048576).toFixed(1)} MB` : ''}</span></div>
    ${files.map(x => `<div class="fcrow${x.written ? '' : ' off'}">
      <span class="fcc">${x.written ? '+' + x.count : '—'}</span>
      <span class="fcn">${esc(x.label)}
        <span class="fcf">${esc(x.rel)}</span></span>
      <span class="fcw count">${esc(x.written ? (x.note || '') : (x.skipped || ''))}</span>
    </div>`).join('')}
    ${(p.review || []).length ? `<div class="fcrow fcrev">
      <span class="fcc">—</span>
      <span class="fcn">Left for you to decide
        <span class="fcf">${p.review.map(r => esc(r.rel) + ' (' + r.hits + ')').join(', ')}</span></span>
      <span class="fcw count">the donor is named here in ways that are a
        judgement, not a list — a trait named after it, an ancillary's condition,
        a prebattle speech</span></div>` : ''}
    ${(p.warnings || []).map(w => `<div class="w-warn fcmsg">${esc(w)}</div>`).join('')}
    ${(p.notes || []).map(n => `<div class="fcmsg count">${esc(n)}</div>`).join('')}
  </div>`;
}

function facCloneClose(){ if(state.fac) state.fac.clone = null; closeModal(); }

function facCloneSet(key, value){
  const c = state.fac.clone;
  if(!c) return;
  // the slot is typed as it will be written: one lower-case word
  c[key] = (key === 'name')
    ? String(value).toLowerCase().replace(/[^a-z0-9_]+/g, '_') : value;
  facCloneRender();
  clearTimeout(state.fac._fcT);
  state.fac._fcT = setTimeout(facClonePreview, key === 'art' ? 0 : 280);
}

async function facClonePreview(){
  const c = state.fac && state.fac.clone;
  if(!c) return;
  if(!c.name){ c.plan = null; c.err = ''; facClonePaint(); return; }
  c.busy = true; c.err = '';
  const note = document.getElementById('fcNote');
  if(note) note.textContent = 'Working out what would change…';
  let r;
  try{ r = await api.post('/api/factions/clone_plan', facCloneBody()); }
  catch(e){ r = {error: String((e && e.message) || e)}; }
  finally{ c.busy = false; }
  if(!state.fac || state.fac.clone !== c) return;   // the dialog moved on
  c.plan = r.plan || null;
  // an error the plan already carries is drawn in place; anything else is ours
  c.err = (r.error && !(r.plan && (r.plan.errors || []).length)) ? r.error : '';
  facClonePaint();
}

function facCloneBody(){
  const c = state.fac.clone;
  return {mod: state.src, source: c.source, new: c.name,
          label: c.label, art: !!c.art};
}

async function facCloneApply(){
  const f = state.fac, c = f.clone, p = c && c.plan;
  if(!p || !p.ok || c.busy) return;
  const files = (p.files || []).filter(x => x.written);
  if(!confirm(`Add faction ${c.name}, copied from ${c.source}?\n\n`
    + files.map(x => `  ${x.rel}  +${x.count}`).join('\n')
    + (p.asset_files ? `\n  ${p.asset_files} art file(s), copied and renamed` : '')
    // the review files live in `review`, not in the note, so this dialog names
    // them itself — it has no row to draw them in the way the plan pane does
    + ((p.review || []).length ? '\n\nLeft for you to decide:\n'
        + p.review.map(r => `  ${r.rel}  (${r.hits} mention(s))`).join('\n') : '')
    + '\n\nEvery file is backed up first, and 🕑 Log undoes the whole faction '
    + 'in one go.\n\n' + (p.notes || []).join('\n\n'))) return;
  c.busy = true;
  facCloneRender();
  let res;
  try{ res = await api.post('/api/factions/clone_apply', facCloneBody()); }
  finally{ c.busy = false; }
  if(res.error){ c.err = res.error; facCloneRender(); toast('✗ ' + res.error, 6000); return; }
  activity('added faction', `${c.name}, cloned from ${c.source} in ${state.src}`);
  const keep = c.name;
  f.clone = null;
  closeModal();
  toast(`Added ${keep} — ${res.files.length} file(s), ${res.asset_files} art file(s). `
        + '🕑 Log can undo it.', 5000);
  await loadFactions();
  facOpen(keep);
}
