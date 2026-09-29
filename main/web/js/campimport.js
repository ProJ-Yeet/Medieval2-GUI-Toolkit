/* campimport.js - Campaign Map: a campaign imported from another mod

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   IMPORT A CAMPAIGN - Phase 73, M7.

   Every name here starts `cim`. It sits in 20b's campaign browser under
   24's New campaign, because it is the same act with a different source:
   a new folder, a new name on the menu, and nothing existing written over.

   THE PLAN IS THE FORM. What the server works out first is what the form
   then offers to change: each faction's slot, a unit for each missing one,
   a religion and a rebel type for each the mod lacks. Change any of them
   and the plan is stale until it is worked out again, so what is written
   is always what was last read.
   ===================================================================== */

function cimNew(mod){
  return {mod, open: false, from: '', loading: false, err: '', d: null,
          campaign: '', name: '', title: '',
          factions: {}, units: {}, religions: {}, rebels: {},
          plan: null, stale: false, busy: false};
}

function cimToggle(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cim || state.cim.mod !== c.mod) state.cim = cimNew(c.mod);
  const k = state.cim;
  k.open = !k.open;
  activity(tt('campimport.import_campaign'), k.open ? tt('campimport.opened_the_import_form') : tt('common.closed_it'));
  cbrPaint();
}

async function cimFrom(src){
  const k = state.cim;
  if(!k) return;
  Object.assign(k, {from: src, d: null, err: '', campaign: '', plan: null,
                    factions: {}, units: {}, religions: {}, rebels: {}});
  if(!src){ cbrPaint(); return; }
  k.loading = true;
  cbrPaint();
  let d;
  try{
    d = await api.get(`/api/campimport?mod=${enc(k.mod)}&from=${enc(src)}`,
                      {label: tt('campimport.reading_s_campaigns',{src})});
  }catch(e){
    if(state.cim !== k) return;
    k.loading = false; k.err = errText(e); cbrPaint(); return;
  }
  if(state.cim !== k || k.from !== src) return;
  k.loading = false;
  k.d = d;
  const rows = d.campaigns || [];
  const first = rows.find(r => r.campaign === 'imperial_campaign') || rows[0];
  k.campaign = first ? first.campaign : '';
  cimDefaultName();
  cbrPaint();
}

//: What the folder is called until somebody types a name: the mod and the
//: campaign, as the bare word a folder has to be. Never the campaign's own
//: name alone, which is usually imperial_campaign and already taken here.
function cimDefaultName(){
  const k = state.cim;
  if(!k || k.named) return;
  const leaf = (k.campaign || '').split('/').pop();
  k.name = `${k.from}_${leaf}`.replace(/[^A-Za-z0-9_-]+/g, '_')
                              .replace(/^[^A-Za-z]+/, '');
}

//: A box typed in: kept, and the plan marked stale, with no repaint - a
//: repaint would take the caret out of the box being typed in.
function cimType(field, value){
  const k = state.cim;
  if(!k) return;
  k[field] = value;
  if(k.plan) k.stale = true;
}

//: One row of a resolution table: which slot, which unit, which religion.
function cimPick(table, key, value){
  const k = state.cim;
  if(!k) return;
  k[table][key] = value;
  if(k.plan) k.stale = true;
  cbrPaint();
}

function cimBody(){
  const k = state.cim;
  return {mod: k.mod, from: k.from, campaign: k.campaign, name: k.name.trim(),
          title: k.title.trim(), factions: k.factions, units: k.units,
          religions: k.religions, rebels: k.rebels};
}

async function cimPlan(){
  const k = state.cim;
  if(!k || k.busy) return;
  k.busy = true;
  cbrPaint();
  let res;
  try{ res = await api.post('/api/campimport/plan', cimBody(),
                            {label: tt('campimport.working_out_the_import')}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.cim !== k) return;
  k.plan = res.plan || {errors: [res.error || tt('common.the_plan_came_back_empty')]};
  k.stale = false;
  cbrPaint();
}

async function cimApply(){
  const k = state.cim;
  if(!k || k.busy || !k.plan || !k.plan.ok || k.stale) return;
  const p = k.plan;
  if(!confirm(tt('campimport.import_confirm',{campaign:p.campaign,source:p.source,mod:k.mod,name:p.name,
    changes:(p.changes || []).join('\n'),
    warnings:(p.warnings || []).length
       ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '',
    files:p.files,size:cnwSize(p.bytes)}))) return;
  k.busy = true;
  cbrPaint();
  let res;
  try{ res = await api.post('/api/campimport/apply', cimBody(),
                            {label: tt('campimport.importing_campaign',{campaign:p.campaign})}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || tt('common.the_import_failed')), 9000);
    cbrPaint();
    return;
  }
  toast(tt('campimport.imported_from_files_undo',{name:res.name,source:p.source,files:res.files}), 7000);
  activity(tt('campimport.import_campaign'), tt('campimport.from',{mod:k.mod,name:res.name,source:p.source,campaign:p.campaign}));
  state.cim = cimNew(k.mod);
  if(state.cnw) state.cnw.d = null;
  if(state.cbr){ state.cbr.d = null; cbrLoad(); }
}

/* ---------- drawing (by cbrPaint, inside the browser's own panel) ---------- */

function cimHtml(){
  const c = state.cmap;
  const k = state.cim && c && state.cim.mod === c.mod ? state.cim : null;
  const head = `<div class="cmbar2">
    <button class="${k && k.open ? 'on' : ''}" onclick="cimToggle()"
      title="${ttA('campimport.bring_a_campaign_out_of_another')}"
      >${tt('campimport.from_another_mod')}</button>
    <span class="sp"></span>
    ${k && k.loading ? `<span class="count">${tt('common.reading_2')}</span>` : ''}
  </div>`;
  if(!k || !k.open) return head;
  const others = (state.mods || []).map(m => m.name).filter(n => n !== k.mod);
  let html = head + `<div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('common.from')}</span>
      <select onchange="cimFrom(this.value)">
        <option value="">${tt('campimport.pick_a_mod')}</option>
        ${others.map(n => `<option value="${esc(n)}"${n === k.from ? ' selected' : ''}
          >${esc(n)}</option>`).join('')}
      </select></span></div>`;
  if(!others.length) return html + `<div class="count">${tt('campimport.no_other_mod_is_installed_to')}</div>`;
  if(k.err) return html + `<div class="w-bad">${esc(k.err)}</div>`;
  const d = k.d;
  if(!k.from || !d) return html;
  const rows = d.campaigns || [];
  if(!rows.length) return html + `<div class="count">${tt('campimport.has_no_campaign_to_import',{x:esc(k.from)})}</div>`;
  html += `<div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('campimport.campaign')}</span>
      <select onchange="cimType('campaign', this.value); cimDefaultName(); cbrPaint()">
        ${rows.map(r => `<option value="${esc(r.campaign)}"${
          r.campaign === k.campaign ? ' selected' : ''}>${tt('campimport.files',{x:esc(r.title || r.leaf),files:r.files,x2:cnwSize(r.bytes)})}</option>`).join('')}
      </select></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('campimport.folder_here')}</span>
      <input value="${esc(k.name)}" placeholder="Imported_Campaign"
        oninput="cimType('name', this.value); state.cim.named = true"></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">${tt('common.on_the_menu')}</span>
      <input value="${esc(k.title)}" placeholder="${ttA('campimport.the_title_it_has_in',{x:esc(k.from)})}"
        oninput="cimType('title', this.value)"></span></div>
    <div class="count">${tt('campimport.it_goes_under_with_its_map',{dir:esc(d.dir),mod:esc(k.mod),mod2:esc(k.mod)})}</div>
    <div class="cmbar2">
      <button onclick="cimPlan()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? tt('common.working_it_out') : (k.plan ? tt('campimport.work_it_out_again') : tt('campimport.work_out_the_import'))}</button>
      <span class="sp"></span>
      ${k.stale ? `<span class="count">${tt('campimport.changed_since_work_it_out_again')}</span>` : ''}
    </div>`;
  return html + cimPlanHtml(k);
}

function cimPlanHtml(k){
  const p = k.plan;
  if(!p) return '';
  const errs = (p.errors || []).length ? `<div class="w-bad">
    ${p.errors.map(e => esc(e)).join('<br>')}</div>` : '';
  return `<div class="cbrrow">
    ${errs}
    ${p.ok ? `<div class="k">${tt('campimport.files_size_into_folder',{files:ttN('campimport.file_count',p.files),size:cnwSize(p.bytes),folder:esc(p.folder)})}</div>` : ''}
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    ${cimFactionsHtml(k, p)}
    ${cimUnitsHtml(k, p)}
    ${cimMapHtml(k, p, 'religions', 'religion', p.religion_names, tt('common.religions'))}
    ${cimMapHtml(k, p, 'rebels', 'rebels', p.rebel_names, tt('campimport.rebel_types'))}
    ${p.ok ? `<div class="cmbar2">
      <button class="primary" onclick="cimApply()" ${k.busy || k.stale ? 'disabled' : ''}
        >${k.busy ? tt('campimport.importing') : tt('campimport.import_as',{name:esc(p.name)})}</button>
      <span class="sp"></span>
      <span class="count">${tt('campimport.nothing_existing_is_written_over_but')}</span>
    </div>` : ''}
  </div>`;
}

function cimFactionsHtml(k, p){
  const rows = (p.factions || []).filter(f => !f.only_creator);
  if(!rows.length) return '';
  const slots = p.slots || [];
  return `<details ${rows.some(f => f.how !== 'same') ? 'open' : ''}>
    <summary>${tt('campimport.factions_on_another_slot',{rows_n:rows.length,n:rows.filter(f => f.how !== 'same').length})}</summary>
    <table class="cimtab"><tr><th>${esc(p.source)}</th><th>${tt('campimport.plays_as')}</th><th></th></tr>
    ${rows.map(f => {
      const want = k.factions[f.source] || f.slot;
      return `<tr><td>${esc(f.source)}</td><td><select
        onchange="cimPick('factions', '${esc(jsq(f.source))}', this.value)">
        ${slots.map(s => `<option value="${esc(s.slot)}"${s.slot === want ? ' selected' : ''}
          >${esc(s.label)}${s.label === s.slot ? '' : ' - ' + esc(s.slot)}</option>`).join('')}
        </select></td><td class="count">${f.source_culture && f.culture
          && f.source_culture !== f.culture
          ? `${esc(f.source_culture)} → ${esc(f.culture)}` : esc(f.culture || '')}</td></tr>`;
    }).join('')}</table></details>`;
}

function cimUnitsHtml(k, p){
  const rows = p.units || [];
  if(!rows.length) return '';
  return `<details open>
    <summary>${tt('campimport.units_lacks_types_regiments',{mod:esc(k.mod),types:ttN('campimport.unit_type_count',rows.length),regiments:rows.reduce((a, u) => a + u.count, 0)})}</summary>
    <div class="count">${tt('campimport.type_one_of_s_units_to',{mod:esc(k.mod)})}</div>
    <datalist id="cimUnitList">${(p.unit_names || []).map(n =>
      `<option value="${esc(n)}">`).join('')}</datalist>
    <table class="cimtab"><tr><th>${tt('campimport.unit')}</th><th>×</th><th>${tt('campimport.becomes')}</th></tr>
    ${rows.map(u => `<tr><td>${esc(u.unit)}</td><td>${u.count}</td><td><input
      list="cimUnitList" value="${esc(k.units[u.unit] !== undefined ? k.units[u.unit] : u.to)}"
      placeholder="${ttA('campimport.left_out')}"
      onchange="cimPick('units', '${esc(jsq(u.unit))}', this.value.trim())"></td></tr>`).join('')}
    </table></details>`;
}

function cimMapHtml(k, p, table, key, names, title){
  const rows = p[table] || [];
  if(!rows.length) return '';
  return `<details open><summary>${tt('campimport.lacks',{title,mod:esc(k.mod),rows_n:rows.length})}</summary>
    <table class="cimtab"><tr><th>${esc(p.source)}</th><th>${tt('campimport.provinces')}</th><th>${tt('campimport.becomes')}</th></tr>
    ${rows.map(r => {
      const want = k[table][r[key]] || r.to;
      return `<tr><td>${esc(r[key])}</td><td>${r.regions}</td><td><select
        onchange="cimPick('${table}', '${esc(jsq(r[key]))}', this.value)">
        ${(names || []).map(n => `<option value="${esc(n)}"${n === want ? ' selected' : ''}
          >${esc(n)}</option>`).join('')}</select></td></tr>`;
    }).join('')}</table></details>`;
}

//: A value dropped into a single-quoted JS string inside an attribute.
function jsq(s){
  return String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}
