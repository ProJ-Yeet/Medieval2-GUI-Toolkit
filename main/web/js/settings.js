/* settings.js - the settings dialog, M2TWEOP folders, and the log/undo panel

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ---- new unit: reuses the transfer engine with source == destination ---- */
function openNewUnitPicker(){
  const modal=document.getElementById('modal');
  const d=state.data||{};
  modal.className='modal';
  modal.innerHTML=`<h2>${tt('settings.new_unit_pick_the_unit_to')}</h2>
    <div class="mbody">
      <div class="count" style="margin-bottom:8px">${tt('settings.the_new_unit_copies_the_one')}</div>
      <input id="nuSearch" placeholder="${ttA('settings.filter_units')}" style="width:100%" oninput="renderNewUnitList()">
      <div class="barrow" style="margin-bottom:6px">
        <select id="nuFac" onchange="renderNewUnitList()">${
          opts(tt('settings.all_factions'),(d.factions||[]),facLabel)}</select>
        <select id="nuCat" onchange="renderNewUnitList()">${opts(tt('settings.all_categories'),d.categories||[])}</select>
        <select id="nuClass" onchange="renderNewUnitList()">${opts(tt('settings.all_classes'),d.classes||[])}</select>
        <label class="chk"><input type="checkbox" id="nuMerc" onchange="renderNewUnitList()"> ${tt('settings.mercs_only')}</label>
        <span class="count" id="nuCount"></span>
      </div>
      <div class="baselist" id="nuList" style="max-height:420px"></div>
    </div>
    <div class="foot"><button onclick="closeModal()">${tt('settings.cancel')}</button></div>`;
  overlay.classList.add('open');
  renderNewUnitList();
}
// A labelled list (factions) is ordered by what it SHOWS, so a picker follows the
// same A→Z as the sidebar; a plain one keeps the order it came in.
// `sel` keeps a picker's choice through a re-render - the armour-tier menu redraws
// on every edit, unlike this dialog, which is built once.
const opts=(allLabel,values,label,sel)=>`<option value="">${allLabel}</option>`+
  (label?[...values].sort((a,b)=>label(a).localeCompare(label(b))):values)
    .map(v=>`<option value="${esc(v)}"${v===sel?' selected':''}>${esc(label?label(v):v)}</option>`).join('');
function renderNewUnitList(){
  const g=id=>(document.getElementById(id)||{}).value||'';
  const qq=g('nuSearch').trim().toLowerCase();
  const fac=g('nuFac'),cat=g('nuCat'),cls=g('nuClass');
  const merc=(document.getElementById('nuMerc')||{}).checked;
  const all=state.data?state.data.units:[];
  const units=all.filter(u=>
    (!qq||u.name.toLowerCase().includes(qq)||u.type.toLowerCase().includes(qq)
      ||u.dictionary.toLowerCase().includes(qq))
    &&(!fac||u.ownership.includes(fac))&&(!cat||u.kind===cat)&&(!cls||u.class===cls)
    &&(!merc||u.mercenary));
  const cnt=document.getElementById('nuCount');
  if(cnt)cnt.textContent=`${units.length}/${all.length}`;
  document.getElementById('nuList').innerHTML=units.slice(0,400).map(u=>`
    <div class="baserow" onclick="startNewUnit('${q1(esc(u.type))}')">
      <img onerror="iconRetry(this)" src="${iconUrl(state.src,u.type)}">
      <div><div>${esc(u.name)}</div><div class="count">${esc(u.type)} · ${esc(u.kind||u.category||'?')}${
        u.class?' / '+esc(u.class):''}${u.mercenary?tt('settings.merc'):''}</div></div>
    </div>`).join('')||`<div class="count" style="padding:8px">${tt('settings.no_units_match')}</div>`;
}
function startNewUnit(type){
  state.dst=state.src; state.destData=null;      // same-mod "transfer" = a new unit
  const u=(state.data.units.find(x=>x.type===type)||{});
  const c=cfgFor(type);
  c.on_conflict='rename';
  c.new_type=type+' (new)';
  c.new_dictionary=(u.dictionary||type)+'_new';
  // …and the name the PLAYER reads, which is a third name and the one this flow
  // is really about: a new type and a new dictionary still leave the unit called
  // whatever the original was called, because the localisation record is copied.
  c.new_name=((u.name||type)+' (new)');
  // nothing needs relocating inside one mod: identical models/cards are reused
  c.asset_conflict='use_existing'; c.icon_conflict='use_existing'; c.engine_conflict='use_existing';
  c._resolved=true;
  openComposer([type]);
}

/* ---------- settings ---------- */
async function openSettings(){
  document.getElementById('modal').className='modal';
  const s=await api.get('/api/settings'); state.settings=s;
  const ign=s.unit_limit_ignored||[];
  const ignHtml=ign.length
    ? ign.map(m=>`<div class="ovr"><span><code>${esc(m)}</code></span><button onclick="reenableLimit('${q1(esc(m))}')">${tt('settings.re_enable_warning')}</button></div>`).join('')
    : `<div class="count">${tt('settings.none_the_500_unit_limit_warning')}</div>`;
  document.getElementById('modal').innerHTML=`<h2>${tt('settings.settings')}</h2>
    <div class="mbody">
      <fieldset><legend>${tt('settings.display')}</legend>
        <label>${tt('settings.interface_size')}
          <select onchange="uiScaleSet(this.value)" style="margin-left:6px">${UI_SCALES.map(p=>
            `<option value="${p}" ${p===(+s.ui_scale||100)?'selected':''}>${p}%</option>`).join('')}</select></label>
        <div class="count" style="margin-top:6px">${tt('settings.draws_the_whole_tool_smaller_or')}</div>
        <label style="display:block;margin-top:10px">${tt('settings.interface_language')}
          <select id="uiLang" onchange="i18nChoose(this.value)" style="margin-left:6px">${i18nOptionsHtml()}</select></label>
        <div class="count" style="margin-top:6px">${tt('settings.interface_language_hint')}</div>
      </fieldset>
      <fieldset><legend>${tt('settings.medieval_ii_root_folder')}</legend>
        <div class="count" style="margin-bottom:8px">${tt('settings.point_to_your_medieval_ii_install')}</div>
        <div style="display:flex;gap:6px">
          <input id="rootInput" style="width:100%" value="${esc(s.med2_root||'')}" placeholder="${ttA('settings.c_total_war_medieval_ii_definitive')}">
          <button onclick="autoDetectRoot()">${tt('settings.auto_detect')}</button>
          <button onclick="browseRoot()">${tt('settings.browse')}</button>
        </div>
        <div id="rootStatus" class="count" style="margin-top:8px"></div>
      </fieldset>
      <fieldset><legend>${tt('settings.launcher')}</legend>
        <label class="chk"><input type="checkbox" id="consoleChk" ${s.show_console?'checked':''} onchange="saveConsole()">
          ${tt('settings.keep_the_console_window_open_the')}</label>
        <div class="count" style="margin-top:6px">${docPoints(
          tt('settings.the_launcher_always_opens_a_console'),
          [tt('settings.off_default_it_closes_once_that'),
           tt('settings.on_it_stays_showing_every_request'),
           tt('settings.on_any_failure_it_comes_back'),
           tt('settings.everything_is_logged_to_config_server')])}</div>
        <div style="margin-top:8px"><button onclick="restartServer()">${tt('settings.restart_now_to_apply_it')}</button>
          <span class="count">${tt('settings.stops_the_tool_and_starts_it')}</span></div>
        <div style="margin-top:8px"><button class="danger" onclick="quitServer()">${tt('settings.quit_server')}</button>
          <span class="count">${tt('settings.stops_the_tool_needed_when_running')}</span></div>
      </fieldset>
      <fieldset><legend>${tt('settings.something_went_wrong')}</legend>
        <div class="count" style="margin-bottom:8px">${tt('settings.everything_the_tool_does_is_recorded')}</div>
        <div><button onclick="closeModal();openLog()">${tt('settings.open_the_log')}</button>
          <span class="count">${tt('settings.the_diagnostic_download_moved_in_there')}</span></div>
      </fieldset>
      <fieldset><legend>${tt('settings.transfer_defaults')}</legend>
        <label class="chk"><input type="checkbox" id="soldierBaseChk" ${s.soldier_from_base?'checked':''} onchange="saveSoldierBase()">
          ${tt('settings.use_the_base_units_soldier_line')}</label>
        <div class="count" style="margin-top:6px">${tt('settings.start_the_soldier_row_on_base')}</div>
      </fieldset>
      <fieldset><legend>${tt('settings.real_world_map_openstreetmap')}</legend>
        <label class="chk"><input type="checkbox" id="osmChk" ${s.osm_enabled?'checked':''} onchange="saveOsm()">
          ${tt('settings.let_the_campaign_maps_real_world')}</label>
        <div class="count" style="margin-top:6px">${docPoints(
          tt('settings.the_one_part_of_the_toolkit'),
          [tt('settings.sent_the_maps_real_world_box'),
           tt('settings.map_tiles_are_kept_on_disk'),
           tt('settings.the_servers_are_below_one_a')])}</div>
        <label style="display:block;margin-top:6px">${tt('settings.map_tiles_and_are_filled_in')}
          <textarea id="osmTiles" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_tiles||['https://tile.openstreetmap.org/{z}/{x}/{y}.png']).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.opentopomap_a_backdrop_style')}
          <textarea id="osmTilesTopo" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_tiles_topo||['https://a.tile.opentopomap.org/{z}/{x}/{y}.png','https://b.tile.opentopomap.org/{z}/{x}/{y}.png','https://c.tile.opentopomap.org/{z}/{x}/{y}.png']).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.osm_humanitarian_a_backdrop_style')}
          <textarea id="osmTilesHot" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_tiles_hot||['https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png','https://b.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png']).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.openhistoricalmap_a_backdrop_style_is_the')}
          <textarea id="osmTilesOhm" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_tiles_ohm||['https://tile.openhistoricalmap.org/historicalmaps/{z}/{x}/{y}.png?date={date}']).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.overpass_the_coastline')}
          <textarea id="osmOverpass" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_overpass||['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.elevation_tiles_the_heights_generator_and')}
          <textarea id="osmElevation" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_elevation||['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png']).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.land_cover_esa_worldcover_as_a')}
          <textarea id="osmLandcover" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_landcover_wms||['https://services.terrascope.be/wms/v2?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=WORLDCOVER_2021_MAP&STYLES=&FORMAT=image/png&TRANSPARENT=FALSE&SRS=EPSG:3857&BBOX={bbox}&WIDTH={width}&HEIGHT={height}']).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.k_ppen_climates_a_wms_optional')}
          <textarea id="osmKoppenWms" rows="2" style="width:100%" onchange="saveOsm()">${esc((s.osm_koppen_wms||[]).join('\n'))}</textarea></label>
        <label style="display:block">${tt('settings.k_ppen_climates_a_file_on')}
          <input id="koppenFile" style="width:100%" placeholder="C:\\maps\\koppen_geiger_0p083.tif" value="${esc(s.koppen_file||'')}" onchange="saveOsm()"></label>
        <label style="display:block">${tt('settings.nominatim_the_place_search')}
          <input id="osmNominatim" style="width:100%" value="${esc(s.osm_nominatim||'https://nominatim.openstreetmap.org')}" onchange="saveOsm()"></label>
      </fieldset>
      <fieldset><legend>${tt('settings.unit_text_cache')}</legend>
        <label class="chk"><input type="checkbox" id="clearBinChk" ${s.clear_strings_bin===false?'':'checked'} onchange="saveClearBin()">
          ${tt('settings.clear_export_units_txt_strings_bin')}</label>
        <div class="count" style="margin-top:6px">${tt('settings.the_game_reads_that_compiled_cache')}</div>
        <div class="count" style="margin-top:6px">${tt('settings.it_is_the_only_file_this')}</div>
      </fieldset>
      <fieldset><legend>${tt('settings.m2ex_mods_no_engine_limits')}</legend>
        <div class="count" style="margin-bottom:8px">${tt('settings.m2ex_replaces_the_engines_hardcoded_tables',{VANILLA_FACTION_LIMIT,VANILLA_UNIT_LIMIT})}</div>
        <div class="count" style="margin-bottom:8px">${tt('settings.two_of_the_engines_ceilings_are')}</div>
        <div class="count" style="margin-bottom:8px">${tt('settings.this_is_not_the_m2tweop_setting')}</div>
        <div class="ovrlist">${(state.mods||[]).map(m=>`<div class="ovr">
          <label class="chk"><input type="checkbox" ${m.m2ex?'checked':''}
            onchange="setM2exFromSettings('${q1(esc(m.name))}',this.checked)"> <code>${esc(m.name)}</code></label>
        </div>`).join('')||`<div class="count">${tt('settings.no_mods_found')}</div>`}</div>
      </fieldset>
      <fieldset><legend>${tt('settings.unit_limit_warning_500_vanilla_cap')}</legend>
        <div class="count" style="margin-bottom:8px">${tt('settings.mods_where_the_unit_warning_is',{VANILLA_UNIT_LIMIT})}</div>
        ${ignHtml}
      </fieldset>
      <fieldset><legend>${tt('settings.m2tweop_unit_folders')}</legend>
        <div class="count" style="margin-bottom:8px">${tt('settings.m2tweop_loads_extra_units_from_its',{VANILLA_UNIT_LIMIT})}</div>
        <div class="count" style="margin-bottom:8px">${tt('settings.left_blank_an_eopdata_folder_is')}</div>
        <div style="display:flex;gap:6px;align-items:center;margin-bottom:8px">
          <select id="eopModSel" onchange="loadEopDirs()" style="max-width:260px">${
            (state.mods||[]).map(m=>`<option value="${esc(m.name)}"${m.name===(state.dst||state.src)?' selected':''}>${esc(m.name)}</option>`).join('')}</select>
          <button onclick="addEopDir()">${tt('settings.add_folder')}</button>
        </div>
        <div id="eopDirs" class="count">${tt('settings.loading')}</div>
      </fieldset>
    </div>
    <div class="foot"><button onclick="closeModal()">${tt('settings.close')}</button><button class="primary" onclick="saveRoot()">${tt('settings.save_scan')}</button></div>`;
  overlay.classList.add('open');
  loadEopDirs();
}

/* ---------- M2EX (per mod) ----------
   The same mark the Home card carries, listed here for every mod at once: the
   settings dialog is where somebody goes to set a machine up, and ticking four
   mods there beats visiting four cards. Both call one endpoint, and Home is
   repainted after so the two never disagree. */
async function setM2exFromSettings(name, on){
  const r = await api.post('/api/m2ex', {mod:name, on:!!on});
  if(r.error){ toast('✗ ' + r.error, 5000); return; }
  const m = (state.mods||[]).find(x => x.name === name);
  if(m) m.m2ex = !!r.m2ex;
  if(state.src === name || state.dst === name){
    state.data = state.destData = null;
    state.tr = state.an = state.fac = state.mf = state.bld = null;
  }
  toast(on ? tt('settings.is_marked_as_m2ex',{name}) : tt('settings.is_no_longer_marked_as_m2ex',{name}));
}

/* ---------- M2TWEOP unit folders (per mod) ---------- */
const eopSelMod=()=>{const s=document.getElementById('eopModSel');return s?s.value:'';};
async function eopApi(body){
  const mod=eopSelMod(); if(!mod) return null;
  return api.post('/api/eop_dirs',Object.assign({mod},body||{}));
}
async function loadEopDirs(){
  const box=document.getElementById('eopDirs'); if(!box)return;
  box.textContent=tt('settings.loading');
  const r=await eopApi({});
  if(!r||r.error){box.innerHTML=`<span class="w-bad">${esc((r&&r.error)||tt('settings.could_not_read'))}</span>`;return;}
  const explicit=r.configured.length>0;
  const rows=(explicit?r.configured:r.detected).map(d=>`<div class="ovr"><span><code>${esc(d)}</code></span>${
    explicit?`<button onclick="removeEopDir('${q1(esc(d))}')">${tt('settings.remove')}</button>`:`<span class="count">${tt('settings.auto_detected')}</span>`}</div>`).join('');
  box.innerHTML=(rows||`<div class="count">${tt('settings.no_eop_folder_found_or_set')}</div>`)
    // The counts need the roster read; the folders above do not. A mod whose
    // export_descr_unit.txt is missing or broken still gets the folder list -
    // with the reason in place of the two numbers, which is the answer anyone
    // opening this panel on that mod is actually after.
    +(r.note?`<div class="count w-warn" style="margin-top:8px">${esc(r.note)}</div>`
      :`<div class="count" style="margin-top:8px"><b>${r.eop_count}</b> ${tt('settings.m2tweop_unit_s_in_file_s',{files_n:r.files.length,edu_count:r.edu_count})}</div>`)
    +(r.files.length?`<div class="flist" style="margin-top:6px">${r.files.slice(0,40).map(f=>`<div class="frow"><span class="fp">${esc(f)}</span></div>`).join('')}${
       r.files.length>40?`<div class="count">${tt('settings.and_more',{files:r.files.length-40})}</div>`:''}</div>`:'')
    +(explicit?`<div class="count" style="margin-top:6px">${tt('settings.remove_them_all_to_go_back')}</div>`:'');
}
async function addEopDir(){
  const r=await api.post('/api/browse_folder',{title:tt('settings.select_the_mods_m2tweop_unit_folder')});
  if(!r.path)return;
  const cur=await eopApi({});
  // an explicit list replaces detection outright, so seed it with what was
  // detected - otherwise adding one folder silently drops the others
  const dirs=(cur.configured.length?cur.configured:cur.detected).slice();
  if(!dirs.includes(r.path)) dirs.push(r.path);
  await eopApi({dirs});
  await refreshMods(state.src,state.dst);
  loadEopDirs();
  toast(tt('settings.eop_folder_saved_the_mods_units'));
}
async function removeEopDir(dir){
  const cur=await eopApi({});
  await eopApi({dirs:(cur.configured||[]).filter(d=>d!==dir)});
  await refreshMods(state.src,state.dst);
  loadEopDirs();
}
async function saveRoot(){const root=document.getElementById('rootInput').value.trim();
  rootStatus.textContent=tt('settings.scanning'); await api.post('/api/settings',{med2_root:root});
  const mods=await api.get('/api/mods');
  rootStatus.innerHTML=mods.length?tt('settings.found',{mods_n:mods.length,x:mods.map(m=>esc(m.name)).join(', ')}):`<span class="w-bad">${tt('settings.no_mods_under_that_folder')}</span>`;
  if(mods.length){await refreshMods(state.src,state.dst);setTimeout(closeModal,700);}
}
async function autoDetectRoot(){
  rootStatus.textContent=tt('settings.looking_up_the_registry');
  const r=await api.get('/api/detect_med2_root');
  if(!r.path){rootStatus.innerHTML=`<span class="w-bad">${tt('settings.not_found_in_the_registry_so')}</span>`;return;}
  document.getElementById('rootInput').value=r.path;
  await saveRoot();
}
async function browseRoot(){
  rootStatus.textContent=tt('settings.opening_folder_browser');
  const r=await api.post('/api/browse_folder',{title:tt('settings.select_your_medieval_ii_total_war')});
  if(!r.path){rootStatus.textContent=tt('settings.cancelled');return;}
  document.getElementById('rootInput').value=r.path;
  await saveRoot();
}

/* ---------- log ----------
   Everything the tool has done, and the way back out of any of it.

   It is PAGED. The whole log used to arrive in one piece and be turned into
   markup in one piece - 480 entries, 1.1 MB of JSON, 600 KB of HTML for a screen
   that shows about six of them - which is why opening it could take minutes.
   The server now answers with a page and the counts the filter needs. */
const LOG_MODES=[
  {id:'',           label:tt('settings.everything')},
  {id:'transfer',   label:tt('settings.transfers')},
  {id:'edit',       label:tt('settings.unit_edits')},
  {id:'bmdb',       label:tt('settings.bmdb')},
  {id:'stratmap',   label:tt('settings.strat_map')},
  {id:'cards',      label:tt('settings.unit_cards')},
  {id:'sounds',     label:tt('settings.sounds')},
  {id:'soundbanks', label:tt('settings.sound_banks')},
  {id:'soundscripts',label:tt('settings.sound_scripts')},
  {id:'buildings',  label:tt('settings.buildings')},
  {id:'traits',     label:tt('settings.traits')},
  {id:'ancillaries',label:tt('settings.ancillaries')},
  {id:'factions',   label:tt('settings.factions')},
  {id:'minorfiles', label:tt('settings.minor_files')},
  {id:'strings',    label:tt('settings.strings')},
  {id:'rawtext',    label:tt('settings.raw_text')},
  {id:'changeset',  label:tt('settings.my_changes')},
];
// What the panel is showing right now: which mode, and how much of it.
state.logView={mode:'',shown:0,entries:[],total:0,counts:{},grand:0};
const LOG_PAGE=40;
async function openLog(mode){
  const v=state.logView;
  // Only a real mode id is one: wired straight to a button, this arrives as the
  // click event, and "[object PointerEvent]" is a filter no entry can match.
  if(typeof mode!=='string')mode=undefined;
  if(mode!==undefined&&mode!==v.mode){v.mode=mode;v.shown=0;v.entries=[];}
  document.getElementById('modal').className='modal';
  overlay.classList.add('open');
  if(!v.entries.length)document.getElementById('modal').innerHTML=
    `<h2>${tt('settings.log')}</h2><div class="mbody"><div class="count">${tt('settings.reading_the_log')}</div></div>`;
  const page=await api.get(`/api/log?mode=${encodeURIComponent(v.mode)}&offset=0`+
    `&limit=${Math.max(LOG_PAGE,v.shown||LOG_PAGE)}`,{label:tt('settings.reading_the_log')});
  v.entries=page.entries; v.total=page.total; v.counts=page.counts;
  v.grand=page.grand_total; v.shown=v.entries.length;
  renderLog();
}
async function logMore(){
  const v=state.logView;
  const page=await api.get(`/api/log?mode=${encodeURIComponent(v.mode)}`+
    `&offset=${v.shown}&limit=${LOG_PAGE}`,{label:tt('settings.reading_more_of_the_log')});
  v.entries=v.entries.concat(page.entries); v.shown=v.entries.length; v.total=page.total;
  renderLog();
}
function renderLog(){
  const v=state.logView;
  const tabs=LOG_MODES.map(m=>{
    const n=m.id?(v.counts[m.id]||0):v.grand;
    if(!n&&m.id)return '';                      // a mode nothing was ever done in
    return `<button class="mftab${v.mode===m.id?' on':''}" onclick="openLog('${m.id}')"
      >${esc(m.label)} <span class="count">${n}</span></button>`;
  }).join('');
  const items=v.entries.map(logItemHtml).join('')
    ||`<div class="empty">${tt('settings.nothing_here_yet')}</div>`;
  const left=v.total-v.shown;
  document.getElementById('modal').innerHTML=`<h2>${tt('settings.log')}</h2>
    <div class="mbody">
      <div class="mftabs">${tabs}</div>
      <div class="trnote">${docPoints(tt('settings.every_write_is_here_and_every'),
        [tt('settings.undo_reverts_just_that_entry'),
         tt('settings.revert_to_here_rolls_that_mod'),
         tt('settings.backed_up_files_are_restored_byte')])}</div>
      ${items}
      ${left>0?`<div style="text-align:center;margin:10px 0">
        <button onclick="logMore()">${tt('settings.show_more',{x:Math.min(left,LOG_PAGE)})}</button>
        <span class="count"> ${tt('settings.of_shown',{shown:v.shown,total:v.total})}</span></div>`
       :(v.total>LOG_PAGE?`<div class="count" style="text-align:center;margin:10px 0">
          ${tt('settings.all_shown',{total:v.total})}</div>`:'')}
    </div>
    <div class="foot">
      <button onclick="downloadDiag()" title="${ttA('settings.the_tools_own_detailed_log_which')}">${tt('settings.save_diagnostic_log')}</button>
      <span class="count">${tt('settings.send_it_along_if_the_tool')}</span>
      <button onclick="closeModal()">${tt('settings.close')}</button></div>`;
}
function logItemHtml(e){
  const id=q1(esc(e.id));
  const undoBtn=e.applied&&!e.undone?`<button class="danger" onclick="doUndo('${id}')">${tt('settings.undo')}</button>`:'';
  // 85: a compaction keeps the packs it replaced until it is undone; this
  // gives their space back and the Undo up
  const forgetBtn=e.action==='pack compact'&&e.applied&&!e.undone&&!e.backup_forgotten
    ?`<button onclick="doForgetPacks('${id}')" title="${ttA('settings.delete_the_packs_this_compaction_replaced')}">${tt('settings.forget_the_old_packs')}</button>`:'';
  const revBtn=e.applied&&!e.undone&&e.newer_count
    ?`<button onclick="doRevert('${id}')" title="${ttA('settings.restore_to_its_state_at_this',{dest:esc(e.dest)})}">${tt('settings.revert_to_here',{newer_count:e.newer_count})}</button>`
    :'';
  return `<div class="log-item ${e.undone?'undone':''}">
    <div class="top"><div><b>${esc(e.resolved_type||e.unit_type||'')}</b> <span class="pill">${
      e.mode==='sounds'?tt('settings.voice_edits_in',{dest:esc(e.dest)})
      :e.mode==='soundbanks'?tt('settings.sound_bank_edited_in',{dest:esc(e.dest)})
      :e.mode==='soundscripts'?tt('settings.sound_script_edited_in',{dest:esc(e.dest)})
      :e.mode==='bmdb'?`${e.action==='cleanup'?tt('settings.cleaned_out_of'):tt('settings.bmdb_edit_in')} ${esc(e.dest)}`
      :e.mode==='stratmap'?tt('settings.strat_map_cleaned_out_of',{dest:esc(e.dest)})
      :e.mode==='cards'?`${e.action==='consolidate'?tt('settings.cards_consolidated_in'):tt('settings.cards_cleaned_out_of')} ${esc(e.dest)}`
      :e.mode==='edit'?`${e.action==='delete'?tt('settings.deleted_in'):tt('settings.edited_in')} ${esc(e.dest)}`
      // 21: a whole file saved as text, and a faction's gaps copied from another
      :e.mode==='rawtext'?tt('settings.raw_text_saved_in',{dest:esc(e.dest)})
      // 52: a change set's records ported onto a version of the mod
      :e.mode==='changeset'?tt('settings.changes_ported_into',{dest:esc(e.dest)})
      :e.mode==='factions'&&e.action==='repair'?tt('settings.repaired_in',{dest:esc(e.dest)})
      // 22a: one fort or watchtower line placed, moved, changed or taken out
      :e.mode==='campmap'&&e.action==='fortification'?tt('settings.in',{x:esc((e.options||{}).what||'edit'),dest:esc(e.dest)})
      // 22b: one trade resource line, the same writer
      :e.mode==='campmap'&&e.action==='resource'?tt('settings.resource_in',{x:esc((e.options||{}).what||'edit'),dest:esc(e.dest)})
      // 81 and 85: a mod's animation packs appended to, or written again
      :e.action==='pack port'?tt('settings.animations_ported_into',{dest:esc(e.dest)})
      :e.action==='pack compact'?tt('settings.animation_packs_compacted_in',{dest:esc(e.dest)})
      :e.mode&&e.mode!=='transfer'?tt('settings.edit_in',{mode:esc(e.mode),dest:esc(e.dest)})
      // a transfer that wrote no unit: its models only, which is what the row
      // would otherwise claim was a unit called after the source's
      :e.action==='models'?tt('settings.battle_models_only',{source:esc(e.source),dest:esc(e.dest)})
                     :`${esc(e.source)} → ${esc(e.dest)}`}</span></div>
      <div style="display:flex;gap:8px;align-items:center"><span class="when">${esc(e.when)}</span>
      ${undoBtn}${forgetBtn}${revBtn}
      ${e.undone?`<span class="pill">${tt('settings.undone')}</span>`:(!e.applied?`<span class="pill">${tt('settings.not_applied')}</span>`:'')}</div></div>
    ${renderSummary(e.summary||'')}${e.summary_cut?`<div class="count">${tt('settings.and_more_characters_in_the_diagnostic',{summary_cut:e.summary_cut})}</div>`:''}</div>`;
}
async function doForgetPacks(id){
  if(!confirm(tt('settings.delete_the_packs_this_compaction_replaced_2')))return;
  const r=await api.post('/api/packs/forget',{id});
  if(r.error){toast(r.error);return;}
  toast(tt('settings.old_packs_deleted_mb_freed',{freed:(r.freed/1048576).toFixed(0)}));openLog();}
async function doUndo(id){const r=await api.post('/api/undo',{id});if(r.error){toast(tt('settings.undo_error')+r.error);return;}
  toast(tt('settings.undone_2'));state.destData=null;openLog();if(state.data)loadSource();}
async function doRevert(id){
  const e=(state.logView.entries||[]).find(x=>x.id===id); if(!e){toast(tt('settings.log_entry_not_found'));return;}
  // counted by the server, which is the only place that has the whole log
  const newer=e.newer_count||0;
  if(!newer){toast(tt('settings.already_at_this_stage_there_is'));return;}
  if(!confirm(tt('settings.revert_to_its_state_right_after',{dest:e.dest})+
      tt('settings.this_undoes_newer_transfer_s_to',{newer,dest:e.dest})+
      tt('settings.all_backed_up_files_edu_localisation'))) return;
  const r=await api.post('/api/revert',{id});
  if(r.error){toast(tt('settings.revert_error')+r.error);return;}
  toast(tt('settings.reverted_to_this_stage_transfer_s',{count:r.count}));
  state.destData=null; openLog(); if(state.data)loadSource();}

/* ---------- the real-world map (Phase 25) ----------
   The switch and the three server lists, saved as they are changed. The map's
   own panel reads them fresh each time it opens, so it follows at once. */
async function saveOsm(){
  const val = id => (document.getElementById(id) || {}).value || '';
  const lines = id => val(id).split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  const on = !!(document.getElementById('osmChk') || {}).checked;
  const body = {osm_enabled: on, osm_tiles: lines('osmTiles'),
                osm_tiles_topo: lines('osmTilesTopo'), osm_tiles_hot: lines('osmTilesHot'),
                osm_tiles_ohm: lines('osmTilesOhm'),
                osm_landcover_wms: lines('osmLandcover'), osm_koppen_wms: lines('osmKoppenWms'),
                koppen_file: val('koppenFile').trim(),
                osm_overpass: lines('osmOverpass'), osm_elevation: lines('osmElevation'),
                osm_nominatim: val('osmNominatim').trim()};
  state.settings = await api.post('/api/settings', body);
  if(state.osm){ state.osm.st = null; if(state.osm.open) osmLoad(); }
  if(state.mgn){ state.mgn.d = null; if(state.mgn.open) mgnToggle().then(mgnToggle); }
  toast(on ? tt('settings.openstreetmap_is_on_for_the_real') : tt('settings.openstreetmap_is_off'));
}
