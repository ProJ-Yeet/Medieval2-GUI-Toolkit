/* campforts.js - Campaign Map: forts, watchtowers and trade resources

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   FORTS AND WATCHTOWERS - Phase 22a, D9.

   Every name here starts `cft`, and there was no `cft` name anywhere in the
   tree before this phase.

   THREE WAYS IN, ONE WRITER. Place one with `＋ Fort` or `＋ Watchtower`,
   which arm 20c's pin, so the next click on the map is the tile. Drag one on
   17d's markers layer. Or pick a province and edit the list. All three end in
   the same `/api/map/object_plan`, the same confirmation and the same undo,
   because in the file they are the same edit - one line.

   WHAT IS DEMIR'S AND WHAT IS NOT. The dialog's fields are his: a tile, a
   fort model with the file's own and the stock ones offered, a culture. The
   region box is his too, and here it is filled in rather than typed: a new
   fort is filed under the province under its tile, which is what 393 of DaC's
   400 are. His writes on confirm and throws the file's formatting away; this
   plans first, says what the save would change and why, and writes one line.

   PYTHON OWNS THE RULES. Whether a culture is a culture, whether a type has a
   battle map, whether the tile is sea, on a settlement or somebody else's:
   stratobj.py decides all of it and it arrives here as sentences. The one
   thing said here without asking is the province under the tile, read off the
   region layer the screen already holds, and it is only ever shown.

   22b: A TRADE RESOURCE IS THE SAME PANEL. One more kind of line and the same
   writer, so it is one more Place button and one more box - its name - rather
   than a screen of its own. Where a new one goes in the file is the server's:
   Reforged heads each province's resources with its name and a new one joins
   its province's group, DaC keeps each name together and a new one follows the
   last of its name. D10 is the ⌖ Move button on a finding: the server names the
   nearest tile that would do, and the button puts it in the form.
   ===================================================================== */

const CFT_ICON = {fort: '▣', watchtower: '△', resource: '◆'};
const CFT_NAME = {fort: tt('campforts.fort'), watchtower: tt('campforts.watchtower'), resource: tt('campforts.resource')};
const CFT_KINDS = ['fort', 'watchtower', 'resource'];

/* ---------- state ---------- */

function cftNew(mod, campaign){
  return {mod, campaign, open: false, loading: false, err: '', d: null,
          sel: null, w: null, was: null, adding: '', busy: false,
          preview: null, all: false};
}

function cftOpen(force){
  const c = state.cmap;
  if(!c) return;
  const was = state.cft;
  const camp = c.campaign || '';
  if(was && was.mod === c.mod && was.campaign === camp && !force){
    cftPaint(); return;
  }
  const k = state.cft = cftNew(c.mod, camp);
  k.open = was ? was.open : false;
  if(k.open) cftLoad(); else cftPaint();
}

async function cftLoad(){
  const k = state.cft, c = state.cmap;
  if(!k || !c) return;
  k.loading = true; k.err = '';
  cftPaint();
  let d;
  try{ d = await api.get(`/api/map/objects?mod=${enc(k.mod)}${cmapCampQ()}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cft !== k) return;
  k.loading = false;
  if(d.error){ k.err = d.error; cftPaint(); return; }
  k.d = d;
  // the row that was open, found again by what it is rather than by index
  if(k.sel){
    const r = cftFind(k.sel);
    if(r) cftSelect(r, true); else { k.sel = null; k.w = null; }
  }
  cftPaint();
}

function cftToggle(){
  const k = state.cft;
  if(!k) return;
  k.open = !k.open;
  if(k.open && !k.d) cftLoad(); else cftPaint();
}

//: A row is a kind on a tile - no two of DaC's 800 forts share one - with its
//: line to tell them apart when two do, as 63 of DaC's resources do.
function cftKey(r){ return {kind: r.kind, line: r.line, x: r.x, y: r.y, name: r.name || ''}; }

function cftFind(key){
  const rows = (state.cft.d && state.cft.d.rows) || [];
  return rows.find(r => r.kind === key.kind && r.line === key.line
                     && r.x === key.x && r.y === key.y)
    || rows.find(r => r.kind === key.kind && r.x === key.x && r.y === key.y
                   && (r.name || '') === (key.name || ''))
    || rows.find(r => r.kind === key.kind && r.line === key.line)
    || null;
}

/* ---------- which rows ---------- */

//: The province picked on the map, by name, or ''.
function cftRegion(){
  const c = state.cmap;
  return (c && c.sel && c.sel.name) || '';
}

//: A province's forts: those filed under it and those standing in it, which
//: are the same rows for 393 of DaC's 400 and differ for the seven worth seeing.
function cftRows(){
  const k = state.cft, d = k && k.d;
  if(!d) return [];
  if(k.all) return d.rows.filter(r => r.findings.length);
  const name = cftRegion().toLowerCase();
  if(!name) return [];
  return d.rows.filter(r => (r.region || '').toLowerCase() === name
                         || (r.province || '').toLowerCase() === name);
}

//: The province under a tile in the file's coordinates, off the layer this
//: screen already holds - shown, never decided on.
function cftProvinceAt(x, y){
  const c = state.cmap;
  if(!c || typeof cmapRegionAt !== 'function') return '';
  const tx = +x, ty = c.man.height - 1 - (+y);
  if(!(tx >= 0 && ty >= 0 && tx < c.man.width && ty < c.man.height)) return '';
  const hit = cmapRegionAt(tx, ty);
  if(hit && typeof hit === 'object') return hit.name || '';
  if(hit === 'settlement' || hit === 'port'){
    const own = cmapMarkerOwner(tx, ty);
    return own ? own.region.name || '' : '';
  }
  return '';
}

/* ---------- the working copy ---------- */

function cftSelect(r, keepPreview){
  const k = state.cft;
  k.sel = cftKey(r); k.adding = '';
  k.w = {kind: r.kind, x: r.x, y: r.y, type: r.type || '', culture: r.culture || '',
         name: r.name || '', region: r.region || ''};
  k.was = JSON.stringify(k.w);
  if(!keepPreview) k.preview = null;
}

function cftPick(i){
  const k = state.cft;
  const r = cftRows()[i];
  if(!k || !r) return;
  const same = k.sel && k.sel.kind === r.kind && k.sel.line === r.line;
  if(same && !k.adding){ k.sel = null; k.w = null; k.preview = null; }
  else cftSelect(r);
  cftPaint();
}

//: 17c's rule, carried over: a click on the map that lands on a fort opens it.
function cftPicked(tile){
  const k = state.cft, c = state.cmap;
  if(!k || !c || !k.open || !k.d || !tile || cftDirty()){ cftPaint(); return; }
  const gx = tile[0], gy = c.man.height - 1 - tile[1];
  const r = k.d.rows.find(x => x.x === gx && x.y === gy);
  // 28a: a click that landed on a fort has filled #cmForts, so its tab
  // surfaces the same way a province's does
  if(r){ k.all = false; cftSelect(r); if(typeof cmapSurface === 'function') cmapSurface('cmForts'); }
  else if(k.w && !k.adding){ k.sel = null; k.w = null; k.preview = null; }
  cftPaint();
}

//: The pin's answer for `＋ Fort`, `＋ Watchtower` and `＋ Resource`: a new one
//: on that tile.
function cftPlace(kind, game){
  const k = state.cft;
  if(!k){ return; }
  if(!k.open){ k.open = true; if(!k.d) cftLoad(); }
  const type = kind === 'fort' ? cftDefaultType() : null;
  k.adding = kind; k.sel = null; k.preview = null;
  k.w = {kind, x: game[0], y: game[1], type: type ? type.name : '',
         culture: type ? type.culture : '',
         name: kind === 'resource' ? cftDefaultName() : '', region: ''};
  k.was = null;
  cftPaint();
  cftPlan();
}

//: The fort model a new fort starts as: the one this file writes most, with
//: the culture it writes it with. Nothing when the file has none to copy.
function cftDefaultType(){
  const v = state.cft.d && state.cft.d.vocab;
  const t = v && (v.fort_types || []).find(x => x.uses);
  return t ? {name: t.name, culture: t.culture} : null;
}

//: The name a new resource starts as: the last one placed this session, else the
//: one the file writes most.
function cftDefaultName(){
  const k = state.cft;
  if(k.lastName) return k.lastName;
  const v = k.d && k.d.vocab;
  const list = ((v && v.resources) || []).slice().sort((a, b) => b.uses - a.uses);
  return list.length ? list[0].name : '';
}

//: D10: the server's nearest tile that would do, put in the form and planned.
function cftNear(x, y){
  const k = state.cft;
  if(!k || !k.w) return;
  k.w.x = x; k.w.y = y;
  cftPaint();
  cftPlan();
}

//: 20c: the pin's answer for the tile of the fort on screen.
function cftPinned(game){
  const k = state.cft;
  if(!k || !k.w){ toast(tt('campforts.the_form_was_closed_before_the'), 5000); return; }
  k.w.x = game[0]; k.w.y = game[1];
  cftPaint();
  cftPlan();
}

const cftDirty = () => {
  const k = state.cft;
  return !!(k && k.w) && (!!k.adding || JSON.stringify(k.w) !== k.was);
};

function cftSet(key, value){
  const k = state.cft;
  if(!k || !k.w) return;
  k.w[key] = (key === 'x' || key === 'y') && /^-?\d+$/.test(String(value).trim())
    ? parseInt(value, 10) : value;
  // a type the file writes with one culture brings that culture with it, the
  // way the file itself pairs them - gondor_fort with gondor on all 50 of DaC's
  if(key === 'type'){
    const v = state.cft.d && state.cft.d.vocab;
    const t = v && (v.fort_types || []).find(x => x.name === value);
    if(t && t.culture){ k.w.culture = t.culture; cftPaint(); }
  }
}

function cftGo(){
  const k = state.cft, c = state.cmap;
  if(!k || !k.w || !c) return;
  const tile = [+k.w.x, c.man.height - 1 - (+k.w.y)];
  if(!(tile[0] >= 0 && tile[1] >= 0 && tile[0] < c.man.width && tile[1] < c.man.height)){
    toast(tt('campforts.is_off_a_map',{x:k.w.x,x2:k.w.y,width:c.man.width,height:c.man.height}), 5000);
    return;
  }
  const keep = JSON.stringify(k.w), sel = k.sel, adding = k.adding, was = k.was;
  cmapGoTile(tile, 10, k.w.region || '');
  // arriving is a pick, and a pick re-opens whatever is on the tile - put the
  // form back the way it was, since going somewhere is not a decision
  k.w = JSON.parse(keep); k.sel = sel; k.adding = adding; k.was = was;
  cftPaint();
}

/* ---------- the save ---------- */

function cftBody(action){
  const k = state.cft, w = k.w;
  const body = {mod: k.mod, campaign: k.campaign, kind: w.kind,
                action: action || (k.adding ? 'add' : 'edit'),
                x: w.x, y: w.y};
  if(w.kind === 'fort'){ body.type = w.type; body.culture = w.culture; }
  if(w.kind === 'resource') body.name = w.name;
  if(k.sel){ body.line = k.sel.line; body.at = [k.sel.x, k.sel.y]; }
  // an existing one keeps its section unless the box names another; a new one
  // is filed by the server under the province under its tile
  if(w.region) body.region = w.region;
  return body;
}

//: A plan without a write, so the form can say what is wrong before Save.
async function cftPlan(){
  const k = state.cft;
  if(!k || !k.w) return;
  let res;
  try{ res = await api.post('/api/map/object_plan', cftBody()); }
  catch(e){ res = {plan: {errors: [errText(e)], warnings: [], changes: []}}; }
  if(state.cft !== k || !k.w) return;
  k.preview = res.plan || {errors: [res.error || '?']};
  cftPaint();
}

async function cftSave(action){
  const k = state.cft;
  if(!k || !k.w || k.busy) return;
  const body = cftBody(action);
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/object_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){
    toast('✗ ' + plan.error, 8000);
    k.preview = plan.plan || null;
    cftPaint();
    return;
  }
  const p = plan.plan || {};
  k.preview = p;
  cftPaint();
  const name = body.kind === 'resource' ? (body.name || 'resource')
    : (CFT_NAME[body.kind] || body.kind).toLowerCase();
  const verb = {add: tt('common.add_2'), delete: tt('common.delete'), edit: tt('common.save'), move: tt('campforts.move')}[p.action || body.action];
  if(!confirm(tt('campforts.the',{verb,name,region:p.region ? ` in ${p.region}` : ''})
    + ((p.changes || []).join('\n') || tt('common.no_visible_change'))
    + ((p.warnings || []).length
       ? '\n\n' + p.warnings.slice(0, 4).map(x => '⚠ ' + x).join('\n') : '')
    + tt('campforts.one_line_of_descr_strat_txt')))
    return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/object_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  activity('fort', tt('campforts.at',{mod:k.mod,x:p.action || body.action,kind:body.kind,body:body.x,body2:body.y}));
  if(body.kind === 'resource' && body.name) k.lastName = body.name;
  if(body.action === 'delete'){ k.sel = null; k.w = null; }
  else k.sel = {kind: body.kind, line: res.line, x: body.x, y: body.y,
                name: body.name || ''};
  k.adding = ''; k.preview = null;
  await cftLoad();
  // the markers layer is drawn from this file too, so it is now a version
  // behind - the same reload 18b does after an event moves
  if(state.cmk && state.cmk.d){ state.cmk.d = null; cmkLoad(); }
}

/* 17d's drag, for a fort, a watchtower or a resource. The drop lands here: the
   panel opens on the one that was dragged, its two numbers change and the save
   it would have made is made - one writer, one confirmation, one undo. */
async function cftDrop(item, game){
  const k = state.cft;
  if(!k) return;
  if(!k.open){ k.open = true; }
  if(!k.d) await cftLoad();
  if(!k.d){ toast(tt('campforts.the_forts_and_resources_could_not'), 6000); return; }
  // a marker's line is 0-based, the panel's the file's own 1-based one
  const r = k.d.rows.find(x => x.kind === item.kind && x.line === item.line + 1
                          && x.x === item.x && x.y === item.y)
    || k.d.rows.find(x => x.kind === item.kind && x.x === item.x && x.y === item.y
                       && (item.kind !== 'resource' || x.name === item.name));
  if(!r){ toast(tt('campforts.that_is_not_in_the_file',{kind:item.kind}), 6000); return; }
  k.all = false;
  cftSelect(r);
  k.w.x = game[0]; k.w.y = game[1];
  cftPaint();
  await cftSave('edit');
}

function cftCancel(){
  const k = state.cft;
  if(!k) return;
  k.sel = null; k.w = null; k.adding = ''; k.preview = null;
  cftPaint();
}

function cftShowAll(){
  const k = state.cft;
  if(!k) return;
  k.all = !k.all;
  cftPaint();
}

/* ---------- drawing ---------- */

function cftPaint(){
  const el = document.getElementById('cmForts');
  if(!el) return;
  el.innerHTML = cftHtml();
}

function cftHtml(){
  const k = state.cft;
  if(!k) return '';
  const d = k.d, n = d ? d.counts : null;
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cftToggle()"
      title="${ttA('campforts.the_forts_watchtowers_and_trade_resources')}">
      ${tt('campforts.forts_and_resources',{open:k.open ? ' ✓' : ''})}</button>
    ${n ? `<span class="count">${tt('campforts.fort_watchtower_resource',{fort:n.fort,fort2:n.fort === 1 ? '' : 's',watchtower:n.watchtower,watchtower2:n.watchtower === 1 ? '' : 's',resource:n.resource || 0,resource2:n.resource === 1 ? '' : 's'})}</span>` : ''}
    ${k.busy ? `<span class="count">${tt('common.working_2')}</span>` : ''}
  </div>`;
  if(!k.open) return head;
  if(k.loading) return head + `<div class="cxpanel count">${tt('campforts.reading_descr_strat_txt')}</div>`;
  if(k.err) return head + `<div class="cxpanel"><div class="w-bad">${esc(k.err)}</div></div>`;
  if(!d) return head;
  return head + `<div class="cxpanel">
    ${cftFileHtml()}
    <div class="csbtns">
      ${tt('campforts.place',{x:CFT_KINDS.map(cftPlaceHtml).join('')})}
    </div>
    ${cftListHtml()}
    ${k.w ? cftFormHtml() : ''}
  </div>`;
}

function cftPlaceHtml(kind){
  const on = state.cpin && state.cpin.fn === 'cftPlace'
    && JSON.stringify(state.cpin.args) === JSON.stringify([kind]);
  return `<button class="${on ? 'on' : ''}"
    onclick="cpinToggle(${esc(JSON.stringify(tt('campforts.the_tile_for_a_new') + kind))}, 'cftPlace', ['${kind}'])"
    title="${ttA('campforts.arm_the_map_the_next_click',{kind})}">
    ＋ ${CFT_ICON[kind]} ${CFT_NAME[kind]} ⌖</button>`;
}

function cftFileHtml(){
  const d = state.cft.d;
  const [good, total] = d.placed_well || [0, 0];
  const bad = d.rows.filter(r => r.findings.some(f => f.fatal)).length;
  const look = d.rows.filter(r => r.findings.length).length;
  const [hg, ht] = d.headed_well || [0, 0];
  return `<div class="count">${tt('campforts.region_section',{file:esc(d.file),sections:d.sections,sections2:d.sections === 1 ? '' : 's',x:total ? tt('campforts.of_forts_and_watchtowers_stand_in',{good,total}) : '',ht:ht
      ? tt('campforts.of_resources_stand_in_the_province',{hg,ht}) : '',x2:d.own_map ? tt('campforts.judged_on_this_campaigns_own_map') : ''})}</div>
    ${look ? `<div class="csbtns"><button class="${state.cft.all ? 'on' : ''}"
      onclick="cftShowAll()">${tt('campforts.to_look_at',{bad:bad ? `<span class="w-bad">${bad}</span> ` : '',look})}</button><span class="count">${tt('campforts.across_the_whole_campaign')}</span></div>` : ''}`;
}

function cftListHtml(){
  const k = state.cft;
  const rows = cftRows();
  const region = cftRegion();
  if(!k.all && !region)
    return `<div class="count">${tt('campforts.pick_a_province_on_the_map')}</div>`;
  const list = rows.map((r, i) => {
    const on = k.sel && !k.adding && k.sel.kind === r.kind && k.sel.line === r.line;
    const bad = r.findings.filter(f => f.fatal).length;
    const where = r.region && r.province && r.region.toLowerCase() !== r.province.toLowerCase()
      ? tt('campforts.under',{kind:r.kind === 'resource' ? 'listed' : 'filed',region:esc(r.region)}) : '';
    return `<div class="cxrow${on ? ' on' : ''}" onclick="cftPick(${i})">
      <b>${CFT_ICON[r.kind]} ${esc(r.kind === 'resource' ? r.name : CFT_NAME[r.kind])}</b>
      <span class="count">${r.x}, ${r.y}${r.type ? ` · ${esc(r.type)}` : ''}${
        r.culture ? ` · ${esc(r.culture)}` : ''}${k.all ? ` · ${esc(r.province || r.region)}` : where}</span>
      ${bad ? `<span class="w-bad">${bad}</span>`
        : r.findings.length ? `<span class="w-warn">${r.findings.length}</span>` : ''}
    </div>`;
  }).join('');
  return `<div class="count">${k.all ? tt('campforts.every_one_with_something_to_look')
      : tt('campforts.in',{region:esc(region)})}</div>
    <div class="cxlist">${list || `<div class="count">${tt('common.none')}</div>`}</div>`;
}

function cftFormHtml(){
  const k = state.cft, w = k.w, v = k.d.vocab || {};
  const here = cftProvinceAt(w.x, w.y);
  const types = v.fort_types || [];
  const cultures = v.cultures;
  const provinces = v.provinces || [];
  const row = k.sel ? cftFind(k.sel) : null;
  const res = w.kind === 'resource';
  // a resource is filed under something only in a file that heads its groups
  const headed = !res || v.grouped_by === 'province';
  const verb = res ? tt('campforts.list') : tt('campforts.file');
  const regionBox = !headed
    ? `<div class="count">${tt('campforts.it_is_traded_by_the_province',{x:v.grouped_by === 'name'
        ? tt('campforts.this_file_keeps_each_resources_lines')
        : tt('campforts.a_new_one_goes_after_the'),here:here ? `: <b>${esc(here)}</b>` : tt('campforts.and_there_is_none')})}</div>`
    : k.adding
    ? `<div class="count">${tt('campforts.under_2',{res:res ? 'listed' : 'filed',x:here ? `<b>${esc(here)}</b>${tt('campforts.the_province_under_the_tile')}` : tt('campforts.the_province_under_the_tile_2'),res2:res
        ? tt('campforts.with_a_heading_of_its_own') : ''})}</div>`
    : `<select onchange="cftSet('region', this.value); cftPaint(); cftPlan()">
        ${provinces.indexOf(w.region) < 0 && w.region
          ? `<option selected>${esc(w.region)}</option>` : ''}
        ${provinces.map(p => `<option${p === w.region ? ' selected' : ''}>${esc(p)}</option>`).join('')}
      </select>
      ${here && here.toLowerCase() !== (w.region || '').toLowerCase()
        ? `<div class="csbtns"><span class="count">${tt('campforts.the_tile_is_in',{here:esc(here)})}</span>
           <button onclick="cftSet('region', ${esc(JSON.stringify(here))}); cftPaint(); cftPlan()"
             >${tt('campforts.it_under',{verb,here:esc(here)})}</button></div>` : ''}`;
  return `<div class="cxform">
    <div class="cmfield"><label>${CFT_ICON[w.kind]} ${k.adding ? tt('campforts.new') + w.kind
      : CFT_NAME[w.kind]}${row ? ` <span class="count">${tt('campforts.line',{line:row.line})}</span>` : ''}</label>
      <div class="cxrow">
        <input style="width:5.5em" value="${esc(String(w.x))}"
          oninput="cftSet('x', this.value)" onchange="cftPlan()">
        <input style="width:5.5em" value="${esc(String(w.y))}"
          oninput="cftSet('y', this.value)" onchange="cftPlan()">
        <span class="count">x, y</span>
        <button onclick="cftGo()" title="${ttA('campforts.put_the_map_on_this_tile')}">◎</button>
        ${cpinButton(tt('campforts.the_tile_for_this',{kind:w.kind}), 'cftPinned', [])}
      </div>
      <div class="count">${tt('campforts.y_counts_up_from_the_bottom')}</div>
    </div>
    ${res ? cftNameHtml(w, v) : ''}
    ${w.kind === 'fort' ? `<div class="csrow2">
      <div class="cmfield"><label>${tt('common.type')}</label>
        <input list="cftTypes" value="${esc(w.type)}"
          oninput="cftSet('type', this.value)" onchange="cftPlan()"
          placeholder="${types.length ? esc(types[0].name) : 'stone_fort_a'}">
        <datalist id="cftTypes">${types.map(t => `<option value="${esc(t.name)}">${
          t.uses ? tt('campforts.in_this_campaign',{uses:t.uses}) : tt('campforts.a_battle_map_folder')}</option>`).join('')}</datalist>
        <div class="count">${v.have_folders
          ? tt('campforts.the_folder_under_settlements_ambient_settlements')
          : tt('campforts.no_settlements_folder_here_to_check')}</div>
      </div>
      <div class="cmfield"><label>${tt('common.culture')}</label>
        ${cultures ? `<select onchange="cftSet('culture', this.value); cftPlan()">
            <option value=""${w.culture ? '' : ' selected'}>(none)</option>
            ${cultures.indexOf(w.culture) < 0 && w.culture
              ? `<option selected>${esc(w.culture)}</option>` : ''}
            ${cultures.map(c => `<option${c === w.culture ? ' selected' : ''}>${esc(c)}</option>`).join('')}
          </select>
          <div class="count">${tt('campforts.from_this_mods_descr_cultures_txt')}</div>`
        : `<input value="${esc(w.culture)}" oninput="cftSet('culture', this.value)"
            onchange="cftPlan()">
          <div class="count">${tt('campforts.descr_cultures_txt_is_not_on')}</div>`}
      </div>
    </div>` : ''}
    <div class="cmfield"><label>${res ? (headed ? tt('campforts.listed_under') : tt('campforts.where_it_goes'))
      : tt('campforts.region_section_2')}</label>${regionBox}</div>
    ${cftFindingsHtml(row)}
    <div class="csbtns">
      ${cftDirty() ? `<button class="primary" onclick="cftSave()">${k.adding
        ? tt('campforts.add_the',{kind:w.kind}) : tt('common.save')}</button>` : ''}
      ${k.adding ? '' : `<button onclick="cftSave('delete')">${tt('common.delete')}</button>`}
      <button onclick="cftCancel()">${k.adding ? tt('common.cancel') : tt('common.close')}</button>
      ${row ? `<button onclick="rtOpen(${esc(JSON.stringify(k.d.file))}, ${row.line})"
        title="${ttA('campforts.open_descr_strat_txt_as_text')}">${tt('campforts.as_text')}</button>` : ''}
    </div>
  </div>`;
}

//: A resource's name, out of descr_sm_resources.txt when the mod ships it.
function cftNameHtml(w, v){
  const names = v.resources || [];
  return `<div class="cmfield"><label>${tt('campforts.resource')}</label>
    <select onchange="cftSet('name', this.value); cftPlan()">
      ${names.some(x => x.name === w.name) ? '' : `<option selected>${esc(w.name)}</option>`}
      ${names.map(x => `<option value="${esc(x.name)}"${x.name === w.name ? ' selected' : ''}>${
        esc(x.name)}${x.uses ? tt('campforts.in_this_campaign_2',{uses:x.uses}) : ''}</option>`).join('')}
    </select>
    <div class="count">${v.have_resources ? tt('campforts.from_this_mods_descr_sm_resources')
      : tt('campforts.descr_sm_resources_txt_is_not')}</div>
  </div>`;
}

//: What is wrong now (the row as the file has it), or what the save would say,
//: and D10's button when the server found a tile that would do.
function cftFindingsHtml(row){
  const k = state.cft, p = k.preview;
  const list = p
    ? (p.errors || []).filter(e => e !== 'nothing to change').map(e => ['w-bad', e])
      .concat((p.warnings || []).map(e => ['w-warn', e]))
    : ((row && row.findings) || []).map(f => [f.fatal ? 'w-bad' : 'w-warn', f.message]);
  const near = p ? p.near
    : (((row && row.findings) || []).find(f => f.near) || {}).near;
  const block = p && p.block && p.opened
    ? `<pre class="cjblock">${esc(p.block)}</pre>` : '';
  if(!list.length && !block) return '';
  return `<div class="cjplan">${list.map(([cls, m]) =>
    `<div class="${cls}">${esc(m)}</div>`).join('')}${near ? `<div class="csbtns">
      <button onclick="cftNear(${+near[0]}, ${+near[1]})"
        title="${ttA('campforts.put_the_nearest_tile_that_would')}">${tt('campforts.move_it_to',{near:+near[0],near2:+near[1]})}</button></div>` : ''}${block}</div>`;
}
