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
  activity('import campaign', k.open ? 'opened the import form' : 'closed it');
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
                      {label: `reading ${src}'s campaigns`});
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
                            {label: 'working out the import'}); }
  catch(e){ res = {plan: {errors: [errText(e)], changes: [], warnings: []}}; }
  finally{ k.busy = false; }
  if(state.cim !== k) return;
  k.plan = res.plan || {errors: [res.error || 'the plan came back empty']};
  k.stale = false;
  cbrPaint();
}

async function cimApply(){
  const k = state.cim;
  if(!k || k.busy || !k.plan || !k.plan.ok || k.stale) return;
  const p = k.plan;
  if(!confirm(`Import ${p.campaign} from ${p.source} into ${k.mod} as ${p.name}?\n\n`
    + (p.changes || []).join('\n')
    + ((p.warnings || []).length
       ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + `\n\n${p.files} file(s), ${cnwSize(p.bytes)}. 🕑 Log can undo it.`)) return;
  k.busy = true;
  cbrPaint();
  let res;
  try{ res = await api.post('/api/campimport/apply', cimBody(),
                            {label: `importing ${p.campaign}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || 'the import failed'), 9000);
    cbrPaint();
    return;
  }
  toast(`${res.name} imported from ${p.source}: ${res.files} file(s). `
    + '🕑 Log can undo it.', 7000);
  activity('import campaign', `${k.mod}: ${res.name} from ${p.source}/${p.campaign}`);
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
      title="Bring a campaign out of another installed mod, with its map, as a new campaign of this one. Its factions are mapped onto this mod's, and whatever this mod lacks is substituted or left out, all named before anything is written."
      >⇲ From another mod</button>
    <span class="sp"></span>
    ${k && k.loading ? '<span class="count">reading…</span>' : ''}
  </div>`;
  if(!k || !k.open) return head;
  const others = (state.mods || []).map(m => m.name).filter(n => n !== k.mod);
  let html = head + `<div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">From</span>
      <select onchange="cimFrom(this.value)">
        <option value="">pick a mod…</option>
        ${others.map(n => `<option value="${esc(n)}"${n === k.from ? ' selected' : ''}
          >${esc(n)}</option>`).join('')}
      </select></span></div>`;
  if(!others.length) return html + `<div class="count">No other mod is
    installed to import from.</div>`;
  if(k.err) return html + `<div class="w-bad">${esc(k.err)}</div>`;
  const d = k.d;
  if(!k.from || !d) return html;
  const rows = d.campaigns || [];
  if(!rows.length) return html + `<div class="count">${esc(k.from)} has no
    campaign to import.</div>`;
  html += `<div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Campaign</span>
      <select onchange="cimType('campaign', this.value); cimDefaultName(); cbrPaint()">
        ${rows.map(r => `<option value="${esc(r.campaign)}"${
          r.campaign === k.campaign ? ' selected' : ''}>${esc(r.title || r.leaf)}
          - ${r.files} files, ${cnwSize(r.bytes)}</option>`).join('')}
      </select></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">Folder here</span>
      <input value="${esc(k.name)}" placeholder="Imported_Campaign"
        oninput="cimType('name', this.value); state.cim.named = true"></span></div>
    <div class="cmtrow"><span class="cmtval">
      <span class="cmtnm">On the menu</span>
      <input value="${esc(k.title)}" placeholder="the title it has in ${esc(k.from)}"
        oninput="cimType('title', this.value)"></span></div>
    <div class="count">It goes under <code>${esc(d.dir)}</code> with its map, so
      ${esc(k.mod)}'s own base map and campaigns are not touched. The factions
      that play it are ${esc(k.mod)}'s.</div>
    <div class="cmbar2">
      <button onclick="cimPlan()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? 'working it out…' : (k.plan ? 'Work it out again' : 'Work out the import')}</button>
      <span class="sp"></span>
      ${k.stale ? '<span class="count">changed since - work it out again</span>' : ''}
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
    ${p.ok ? `<div class="k">${p.files} file${p.files === 1 ? '' : 's'},
      ${cnwSize(p.bytes)} <span class="count">into <code>${esc(p.folder)}</code></span></div>` : ''}
    ${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    ${cimFactionsHtml(k, p)}
    ${cimUnitsHtml(k, p)}
    ${cimMapHtml(k, p, 'religions', 'religion', p.religion_names, 'Religions')}
    ${cimMapHtml(k, p, 'rebels', 'rebels', p.rebel_names, 'Rebel types')}
    ${p.ok ? `<div class="cmbar2">
      <button class="primary" onclick="cimApply()" ${k.busy || k.stale ? 'disabled' : ''}
        >${k.busy ? 'importing…' : `Import as ${esc(p.name)}`}</button>
      <span class="sp"></span>
      <span class="count">Nothing existing is written over but the text keys it
        adds. 🕑 Log can undo it.</span>
    </div>` : ''}
  </div>`;
}

function cimFactionsHtml(k, p){
  const rows = (p.factions || []).filter(f => !f.only_creator);
  if(!rows.length) return '';
  const slots = p.slots || [];
  return `<details ${rows.some(f => f.how !== 'same') ? 'open' : ''}>
    <summary>Factions - ${rows.length}, ${rows.filter(f => f.how !== 'same').length}
      on another slot</summary>
    <table class="cimtab"><tr><th>${esc(p.source)}</th><th>plays as</th><th></th></tr>
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
    <summary>Units ${esc(k.mod)} lacks - ${rows.length} type${rows.length === 1 ? '' : 's'},
      ${rows.reduce((a, u) => a + u.count, 0)} regiments</summary>
    <div class="count">Type one of ${esc(k.mod)}'s units to stand in for each, or
      leave it blank to leave it out. Unit Transfer brings the unit itself.</div>
    <datalist id="cimUnitList">${(p.unit_names || []).map(n =>
      `<option value="${esc(n)}">`).join('')}</datalist>
    <table class="cimtab"><tr><th>unit</th><th>×</th><th>becomes</th></tr>
    ${rows.map(u => `<tr><td>${esc(u.unit)}</td><td>${u.count}</td><td><input
      list="cimUnitList" value="${esc(k.units[u.unit] !== undefined ? k.units[u.unit] : u.to)}"
      placeholder="left out"
      onchange="cimPick('units', '${esc(jsq(u.unit))}', this.value.trim())"></td></tr>`).join('')}
    </table></details>`;
}

function cimMapHtml(k, p, table, key, names, title){
  const rows = p[table] || [];
  if(!rows.length) return '';
  return `<details open><summary>${title} ${esc(k.mod)} lacks - ${rows.length}</summary>
    <table class="cimtab"><tr><th>${esc(p.source)}</th><th>provinces</th><th>becomes</th></tr>
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
