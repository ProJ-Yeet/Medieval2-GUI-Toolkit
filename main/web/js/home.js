/* home.js - Home mode: the mods this machine has, and what each one is ready for

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ======================= HOME =======================
   The toolkit used to open on whichever module you were last in, pointed at
   whichever mod you were last looking at, with no way to see either choice
   except by reading the two dropdowns in the header. Home is the landing page
   that answers both up front: here are your mods, here is what each one has on
   disk, here is what you can do with it.

   Each card asks the server (`/api/mod_files`) which of the files a module reads
   are actually there, so a module that cannot work on this mod says why on the
   card instead of being found out three clicks later. That report is read-only
   and shallow - file stats and an encoding sniff, never a parse - and it is
   cached per mod for the session, because it is a landing page and it has to
   feel like one.

   Nothing here is a second copy of the mod list: it is `state.mods`, the same
   one the header dropdown uses. */

// mod name -> its /api/mod_files report, or 'loading' / {error}
const HOME_REPORTS = {};

function renderHome(){
  const mods = state.mods || [];
  count.textContent = mods.length ? ttN('home.mods_count', mods.length) : '';
  if(!mods.length){
    main.innerHTML = `<div class="empty">${tt('home.no_mods_found_click_settings_and')}
      <br><br><button class="primary" onclick="openSettings()">${tt('home.settings')}</button></div>`;
    return;
  }
  main.innerHTML = `<div class="homewrap">
    ${homeRootHtml()}
    <div class="homestep">
      <span class="n">2</span>
      <span class="t"><b>${tt('home.pick_a_mod_then_a_module')}</b>
        <div class="p">${tt('home.every_write_is_backed_up_log')}</div></span>
    </div>
    ${homeResumeHtml()}
    <div class="homegrid">${mods.map(homeCardHtml).join('')}</div>
    ${homePrefsHtml()}
  </div>`;
  mods.forEach(m => homeLoadReport(m.name));
}

// Step 1 of using the toolkit at all: it has to know where Medieval II lives,
// because every mod it can see is a folder under that root.
//
// The buttons are the same two the settings dialog has, put here directly: a step
// that says "your mods live here" and then sends you to a dialog to change it is
// one hop longer than it needs to be, and the dialog is a worse place to do it
// from - this line is what you are looking at when you notice it is wrong.
function homeRootHtml(){
  const root = state.settings.med2_root || '';
  return `<div class="homestep">
    <span class="n">1</span>
    <span class="t">
      ${tt('home.root_mod_folder_the_medieval_ii')}
      <div class="p">${root ? esc(root) : tt('home.not_set_yet')}</div>
      <div class="count" id="homeRootStatus"></div>
    </span>
    <button onclick="homeAutoDetect()" title="${ttA('home.look_the_install_path_up_from')}">${tt('home.auto_detect')}</button>
    <button class="${root ? '' : 'primary'}" onclick="homeBrowseRoot()">${tt('home.browse')}</button>
  </div>`;
}
// Both reuse the settings dialog's own actions, then re-read the mods and repaint
// Home - the point of doing it here is that the card grid below answers straight
// away whether the folder was the right one.
async function homeSetRoot(path){
  const st = document.getElementById('homeRootStatus');
  if(st) st.textContent = tt('home.reading_path',{path});
  const r = await api.post('/api/settings', {med2_root: path});
  state.settings = r;
  await refreshMods(state.src, state.dst);
  // the per-mod reports belong to the folder that has just been replaced
  for(const k of Object.keys(HOME_REPORTS)) delete HOME_REPORTS[k];
  render();
}
async function homeBrowseRoot(){
  const r = await api.post('/api/browse_folder', {title:tt('home.pick_your_medieval_ii_folder_it')});
  if(!r.path) return;
  await homeSetRoot(r.path);
}
async function homeAutoDetect(){
  const st = document.getElementById('homeRootStatus');
  if(st) st.textContent = tt('home.looking_for_a_medieval_ii_install');
  const r = await api.get('/api/detect_med2_root');
  if(!r.path){
    if(st) st.innerHTML = `<span class="w-warn">${tt('home.no_install_found_in_the_registry')}</span>`;
    return;
  }
  await homeSetRoot(r.path);
}

// Step 3: the settings that are worth having in front of you rather than behind a
// dialog. The dialog stays - it owns the awkward ones (the M2TWEOP folders, the
// unit-limit overrides) - but nothing here should need it.
function homePrefsHtml(){
  const s = state.settings || {};
  // One row per preference: the tick box and its label on the left, the hint
  // right-aligned, so the rows line up down the page.
  const chk = (id, on, label, hint) => `<div>
      <label class="chk"><input type="checkbox" id="${id}"
        ${on ? 'checked' : ''} onchange="homePref(this)"> ${label}</label>
      ${hint ? `<span class="count">${hint}</span>` : ''}</div>`;
  return `<div class="homestep">
    <span class="n">3</span>
    <span class="t">
      <b>${tt('home.preferences')}</b>
      <div class="homeprefs">
        ${chk('prefConsole', s.show_console, tt('home.keep_the_console_window_open'),
              tt('home.from_the_next_launch'))}
        ${chk('prefSoldierBase', s.soldier_from_base, tt('home.start_the_soldier_row_on_base'),
              tt('home.in_a_transfer'))}
        ${chk('prefClearBin', s.clear_strings_bin, tt('home.recompile_strings_bin_after_a_text'),
              tt('home.the_game_reads_the_compiled_copy'))}
        ${chk('prefCodeView', s.code_view, tt('home.show_code_view_beside_the_guided'),
              tt('home.the_raw_lines_live'))}
        <div>
          <label class="chk" style="gap:6px">${tt('home.faction_names_lead_with')}
            <select id="prefFacSort" onchange="homePref(this)">
              <option value="name" ${s.faction_sort!=='code'?'selected':''}>${tt('home.the_in_game_name')}</option>
              <option value="code" ${s.faction_sort==='code'?'selected':''}>${tt('home.the_edu_code')}</option>
            </select></label>
          <span class="count">${tt('home.the_other_one_follows_in_brackets')}</span>
        </div>
      </div>
    </span>
    <button onclick="openSettings()" title="${ttA('home.m2tweop_folders_the_500_unit_limit')}">${tt('home.all_settings')}</button>
  </div>`;
}
// One handler for the lot: the id says which setting, so adding a row above needs
// nothing here.
const HOME_PREF_KEY = {prefConsole:'show_console', prefSoldierBase:'soldier_from_base',
  prefClearBin:'clear_strings_bin', prefCodeView:'code_view', prefFacSort:'faction_sort'};
async function homePref(el){
  const key = HOME_PREF_KEY[el.id]; if(!key) return;
  const value = el.tagName === 'SELECT' ? el.value : !!el.checked;
  state.settings[key] = value;
  await api.post('/api/settings', {[key]: value});
  if(key === 'faction_sort'){
    facSort.value = facBy();
    if(state.data) buildFilter('factionFilter', state.data.factions, 'faction', true);
  }
  toast(tt('home.saved'));
}

// The module you were last in, offered rather than jumped into: landing
// somewhere you did not ask for is exactly what Home exists to stop.
function homeResumeHtml(){
  const last = state.settings.mode;
  if(!last || last === 'home' || !modeOffered(last)) return '';
  const d = modeDef(last);
  const mod = state.src || '';
  return `<div class="homeresume">
    <span class="count">${tt('home.last_time_you_were_in')}</span>
    <button class="primary" onclick="homeGo('${q1(esc(mod))}','${esc(d.id)}')">
      ${d.icon} ${esc(d.name)}${mod?`: ${esc(mod)}`:''} →</button>
  </div>`;
}

function homeCardHtml(m){
  const r = HOME_REPORTS[m.name];
  // The mod's FOLDER name, never its campaign title. The two disagree often
  // enough ("War of the Ring" is Divide_and_Conquer_EUR) that showing the title
  // means the card and every dropdown in the app name different things.
  return `<section class="homecard" id="hc-${esc(homeKey(m.name))}">
    <div class="hchead">
      <div>
        <div class="nm">${esc(m.name)}</div>
        <div class="sub" title="${esc(m.root)}">${esc(m.root)}</div>
      </div>
      ${m.pack?`<span class="badge">${tt('home.mounted_pack')}</span>`:''}
    </div>
    ${homeM2exHtml(m)}
    <div class="hcmods">${homeModulesHtml(m, r)}</div>
    <div class="hcfiles">${homeLaunchHtml(m, r)}${homePacksHtml(m)}${homeFilesHtml(m, r)}</div>
  </section>`;
}
// ids have to survive a mod folder called anything at all
const homeKey = name => (''+name).replace(/[^A-Za-z0-9_-]/g,'_');

/* ---- M2EX ----
   Marked here, on the mod's own card, because it is a fact ABOUT THE MOD rather
   than a preference: the person who installed it knows, nothing in data/ says
   so, and there is no cheaper place to be asked than the page that already
   lists the mods.

   It is not the M2TWEOP setting further down in ⚙ Settings and must not be
   confused with it. That one says where a mod keeps extra unit FILES. This one
   says the engine's hardcoded tables have been replaced, so the ceilings the
   toolkit checks against - 31 factions, 500 units, a trait's 9 levels, an
   ancillary's 8 effects, a building's 32 recruitment slots - are not this mod's
   ceilings and reporting them is noise. Every other check still runs. */
function homeM2exHtml(m){
  return `<label class="chk hcm2ex" title="${ttA('home.tick_this_only_for_a_mod',{VANILLA_UNIT_LIMIT})}">
    <input type="checkbox" ${m.m2ex?'checked':''}
      onchange="homeSetM2ex('${q1(esc(m.name))}',this.checked)">
    ${tt('home.runs_on_m2ex_no_engine_limits')}</label>`;
}
async function homeSetM2ex(name, on){
  const r = await api.post('/api/m2ex', {mod:name, on:!!on});
  if(r.error){ toast('✗ ' + r.error, 5000); return; }
  const m = (state.mods||[]).find(x => x.name === name);
  if(m) m.m2ex = !!r.m2ex;
  // the mark decides what every editor reports about this mod, so what is
  // already loaded from it is out of date
  if(state.src === name || state.dst === name){
    state.data = state.destData = null;
    state.tr = state.an = state.fac = state.mf = state.bld = null;
  }
  toast(on ? tt('home.is_marked_as_m2ex_its_engine',{name})
           : tt('home.is_no_longer_marked_as_m2ex',{name}), 4500);
  renderHome();
}

function homeModulesHtml(m, r){
  if(!r) return `<span class="count">${tt('home.reading_the_mods_files')}</span>`;
  if(r.error) return `<span class="w-bad">✗ ${esc(r.error)}</span>`;
  return menuModes().filter(d => d.id !== 'home').map(d => {
    const s = r.modules[d.id];
    if(!s) return '';
    const why = s.ready
      ? (s.partial.length ? tt('home.works_but_this_mod_has_no',{partial:s.partial.join(', ')}) : d.hint)
      : tt('home.needs_and_this_mod_has_none',{missing:s.missing.join(', ')});
    return `<button class="hcmod${s.ready?'':' off'}" title="${esc(why)}"
      onclick="homeGo('${q1(esc(m.name))}','${esc(d.id)}')">
      <span class="ic">${d.icon}</span><span class="nm">${esc(d.name)}</span>
      ${s.ready?(s.partial.length?'<span class="dot warn">●</span>':'')
              :'<span class="dot bad">●</span>'}</button>`;
  }).join('');
}

/* ---- will the game start it (58) ----
   Every way the mod folder offers to start the game - a .bat, the M2TWEOP
   launcher, a bare .cfg - and what is wrong with each, from the files the game
   and the launchers read (launchcheck.py). One line shut; the routes open. */
function homeLaunchHtml(m, r){
  const L = r && r.launch;
  if(!L) return '';
  const key = '_launch_' + m.name, open = !!HOME_REPORTS[key];
  const head = {ready: `<span class="w-good">✓</span> ${tt('home.will_start')}`,
                warn: `<span class="w-warn">●</span> ${tt('home.will_start_with_warnings')}`,
                broken: `<span class="w-bad">✗</span> ${tt('home.no_way_to_start_it_works')}`,
                none: `<span class="w-warn">●</span> ${tt('home.no_bat_launcher_or_cfg_to')}`,
                unknown: `<span class="count">?</span> ${tt('home.could_not_be_read')}`}[L.verdict] || '';
  const rows = (L.routes || []).map(x => `<tr>
      <td class="s">${x.ok ? (x.warnings.length ? '<span class="w-warn">●</span>' : '<span class="w-good">✓</span>')
                           : '<span class="w-bad">✗</span>'}</td>
      <td>${esc(x.how)}<div class="count">${esc(x.cfg || tt('home.no_cfg'))} · ${esc(x.exe || '?')}${
        x.laa === true ? tt('home.large_address_aware') : x.laa === false ? ` ${tt('home.not_large_address_aware')}` : ''}</div>
        ${[...x.faults.map(t => `<div class="w-bad">${esc(t)}</div>`),
           ...x.warnings.map(t => `<div class="w-warn">${esc(t)}</div>`),
           ...x.notes.map(t => `<div class="count">${esc(t)}</div>`)].join('')}</td></tr>`).join('');
  const reg = L.registry && L.registry.read
    ? `<div class="count">${L.registry.entry
        ? tt('home.the_disk_launcher_knows_it_registry',{entry:esc(L.registry.entry)})
        : tt('home.no_launcher_registry_entry_only_the')}</div>` : '';
  return `<button class="hctoggle" onclick="homeToggle('${q1(esc(key))}')">
      ${tt('home.launch',{open:open ? '▾' : '▸',head})}</button>
    ${open ? `<table class="hctab">${rows}</table>${reg}` : ''}`;
}
function homeToggle(key){ HOME_REPORTS[key] = !HOME_REPORTS[key]; renderHome(); }

/* ---- the animation packs (85) ----
   What the mod's pack.dat and skeletons.dat hold that nothing plays: a copy of
   a path at a scale it already has (the game plays the first), a copy at a
   scale no skeleton has, a path no slot names, a skeleton listed twice. Read
   only when opened; "Compact" writes the packs again holding what is played,
   as a job of its own that Undo takes back. */
function homePacksHtml(m){
  const key = '_packs_' + m.name, open = !!HOME_REPORTS[key], P = HOME_REPORTS['_packsr_' + m.name];
  let head = '';
  if(P && !P.error){
    const waste = P.anim_freed + P.skel_freed;
    head = waste ? `<span class="w-warn">●</span> ${tt('home.nothing_plays',{x:homeSize(waste)})}`
                 : `<span class="w-good">✓</span> ${tt('home.everything_in_them_is_played')}`;
  } else if(P && P.error) head = `<span class="count">${esc(P.error)}</span>`;
  const btn = `<button class="hctoggle" onclick="homePacksToggle('${q1(esc(m.name))}')">
      ${tt('home.animation_packs',{open:open ? '▾' : '▸',x:head ? ': ' + head : ''})}</button>`;
  if(!open) return `<div>${btn}</div>`;
  if(!P) return `<div>${btn}<div class="count">${tt('home.reading_the_packs')}</div></div>`;
  if(P.error) return `<div>${btn}</div>`;
  const row = (n, bytes, what) => `<tr><td class="r">${n.toLocaleString()}</td><td class="r count">${homeSize(bytes)}</td><td>${what}</td></tr>`;
  const dupNote = P.duplicate_paths
    ? `<div class="count">${tt('home.path_s_are_listed_more_than',{duplicate_paths:P.duplicate_paths.toLocaleString(),x:P.duplicate_paths_same_scale ? tt('home.of_them_at_one_scale_twice',{duplicate_paths_same_scale:P.duplicate_paths_same_scale})
          : tt('home.every_copy_at_its_own_scale')})}</div>` : '';
  const twice = P.skel_twice.length
    ? `<div class="w-warn">${tt('home.skeletons_listed_twice_the_first_is',{x:P.skel_twice.map(esc).join(', ')})}</div>` : '';
  const unnamed = P.unnamed.length
    ? `<details><summary class="count">${tt('home.skeleton_s_no_battle_or_strat',{unnamed_n:P.unnamed.length})}</summary>
        <div class="count">${tt('home.kept_by_a_compaction_all_the')}</div>
        <div class="count">${P.unnamed.map(esc).join(', ')}</div></details>` : '';
  const act = P.worth_compacting
    ? `<div><button onclick="homePacksCompact('${q1(esc(m.name))}')">${tt('home.compact_the_packs')}</button>
        <span class="count">${tt('home.keeps_animation_s_and_skeleton_s',{keep_anims:P.keep_anims.toLocaleString(),keep_skels:P.keep_skels.toLocaleString()})}</span></div>`
    : '';
  return `<div>${btn}<table class="hctab">
      ${row(P.anims, P.anim_bytes, tt('home.animations_in_pack_dat'))}
      ${row(P.dead, P.dead_bytes, tt('home.dead_copies_a_path_again_at'))}
      ${row(P.other_scale, P.other_scale_bytes, tt('home.copies_at_a_scale_no_skeleton'))}
      ${row(P.unused, P.unused_bytes, tt('home.no_slot_of_any_skeleton_names'))}
      ${row(P.skeletons, P.skel_bytes, tt('home.skeletons_in_skeletons_dat'))}
    </table>${dupNote}${twice}${P.missing_slots ? `<div class="w-bad">${tt('home.slot_s_name_a_path_pack',{missing_slots:P.missing_slots})}</div>` : ''}${unnamed}${act}</div>`;
}
async function homePacksToggle(name){
  const key = '_packs_' + name;
  HOME_REPORTS[key] = !HOME_REPORTS[key];
  renderHome();
  if(HOME_REPORTS[key] && !HOME_REPORTS['_packsr_' + name]){
    let r;
    try{ r = await api.get('/api/packs/housekeeping?mod=' + encodeURIComponent(name)); }
    catch(e){ r = {error: '' + e}; }
    HOME_REPORTS['_packsr_' + name] = r;
    if(state.mode === 'home') renderHome();
  }
}
async function homePacksCompact(name){
  const P = HOME_REPORTS['_packsr_' + name];
  if(!P) return;
  const ok = confirm(tt('home.confirm_compact',{name,keep_anims:P.keep_anims.toLocaleString(),
    freed:homeSize(P.anim_freed + P.skel_freed)}));
  if(!ok) return;
  let r;
  try{ r = await api.post('/api/packs/compact', {mod: name}); }
  catch(e){ r = {error: '' + e}; }
  if(r.error) return toast(r.error);
  toast(r.summary);
  delete HOME_REPORTS['_packsr_' + name];
  HOME_REPORTS['_packs_' + name] = false;
  homePacksToggle(name);                       // open again, read afresh
}

function homeFilesHtml(m, r){
  if(!r || r.error) return '';
  const key = homeKey(m.name);
  const bad = r.files.filter(f => f.state === 'missing' || f.state === 'unreadable');
  const open = !!HOME_REPORTS['_open_' + m.name];
  return `<button class="hctoggle" onclick="homeToggleFiles('${q1(esc(m.name))}')">
      ${tt('home.known_files',{open:open?'▾':'▸',files_n:r.files.length,bad:bad.length?tt('home.missing',{bad_n:bad.length}):tt('home.all_present')})}
    </button>
    ${open?`<table class="hctab">${r.files.map(homeFileRow).join('')}</table>`:''}`;
}
function homeFileRow(f){
  const mark = {present:'<span class="w-good">✓</span>',
                compiled:'<span class="w-good">✓</span>',
                empty:'<span class="w-warn">○</span>',
                missing:f.required?'<span class="w-bad">✗</span>':'<span class="count">·</span>',
                unreadable:'<span class="w-bad">!</span>'}[f.state] || '';
  const size = f.state === 'missing' ? ''
    : f.folder ? ttN('home.n_items', f.size) : homeSize(f.size);
  return `<tr title="${esc(f.note || f.rel)}">
    <td class="s">${mark}</td>
    <td>${esc(f.label)}<div class="count">${esc(f.rel)}</div></td>
    <td class="count r">${esc(size)}</td>
    <td class="count">${esc(f.encoding || '')}</td></tr>`;
}
const homeSize = n => n >= 1048576 ? (n/1048576).toFixed(1)+' MB'
  : n >= 1024 ? Math.round(n/1024)+' KB' : n+' B';

function homeToggleFiles(name){
  HOME_REPORTS['_open_' + name] = !HOME_REPORTS['_open_' + name];
  renderHome();
}

async function homeLoadReport(name){
  if(HOME_REPORTS[name] || HOME_REPORTS['_busy_' + name]) return;
  HOME_REPORTS['_busy_' + name] = true;
  let r;
  try{ r = await api.get('/api/mod_files?mod=' + encodeURIComponent(name)); }
  catch(e){ r = {error: '' + e}; }
  HOME_REPORTS['_busy_' + name] = false;
  HOME_REPORTS[name] = r;
  if(state.mode !== 'home') return;           // they moved on while this loaded
  // repaint just this card, so a slow mod does not restart every other card's
  // load by redrawing the whole grid
  const el = document.getElementById('hc-' + homeKey(name));
  const m = (state.mods || []).find(x => x.name === name);
  if(el && m) el.outerHTML = homeCardHtml(m);
}

/* Open a module on a mod: the two choices the header dropdowns hold, made in one
   click. Both go through the same paths the dropdowns do, so nothing here is a
   second way of changing the mod. */
async function homeGo(name, mode){
  if(name && name !== state.src){
    srcSel.value = name;
    await srcSel.onchange({target: srcSel});
  }
  setAppMode(mode);
}
