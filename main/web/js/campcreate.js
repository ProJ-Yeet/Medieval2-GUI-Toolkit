/* Campaign creation shortcuts reuse the existing validated editors and saves. */
function cmapCreatePaint(){
  const el = document.getElementById('cmCreate'), c = state.cmap;
  if(!el || !c) return;
  const k = state.cmk, factions = k && k.d ? k.d.factions || {} : {};
  const faction = c.createFaction || (c.sel && c.sel.faction) || '';
  const type = c.createType || 'general';
  el.innerHTML = `<div class="cmcreate">
    <div class="cmcreateintro">${tt('campcreate.create_on_the_map_choose_what')}</div>
    <section><h3>${tt('campcreate.regions_settlements')}</h3><div class="cmcreategrid">
      <button class="primary" onclick="cmapCreateRegion()">${tt('campcreate.new_region_name_paint_settlement_port')}</button>
      <button onclick="cmapCreateMarker('settlement')">${tt('campcreate.settlement_marker_add_or_move_on')}</button>
      <button onclick="cmapCreateMarker('port')">${tt('campcreate.port_marker_add_or_move_on')}</button>
      <button onclick="cmapCreateSettlement()">${tt('campcreate.settlement_details_owner_buildings_level')}</button>
    </div><p>${tt('campcreate.select_a_region_first_for_markers')}</p></section>
    <section><h3>${tt('campcreate.characters_armies')}</h3>
      <label>${tt('common.faction')}<select aria-label="${ttA('campcreate.new_character_faction')}" onchange="state.cmap.createFaction=this.value">
        <option value="">${tt('campcreate.choose_a_faction')}</option>${Object.entries(factions).map(([id,f]) =>
          `<option value="${esc(id)}"${id === faction ? ' selected' : ''}>${esc(f.label || id)}</option>`).join('')}
      </select></label>
      <label>${tt('campcreate.character_type')}<select aria-label="${ttA('campcreate.new_character_type')}" onchange="state.cmap.createType=this.value">
        ${Object.keys(CMK_CHAR).map(t => `<option value="${esc(t)}"${t === type ? ' selected' : ''}>${esc(t)}</option>`).join('')}
      </select></label>
      <button onclick="cmapCreateCharacter()" ${Object.keys(factions).length ? '' : 'disabled'}>${tt('campcreate.place_character_army')}</button>
      <button onclick="cmapCreateHorde()" ${Object.keys(factions).length ? '' : 'disabled'}
        title="${ttA('campcreate.for_a_faction_that_holds_nothing')}">${tt('campcreate.horde_start')}</button>
      <p>${k && k.err ? esc(k.err) : !Object.keys(factions).length ? tt('campcreate.campaign_factions_are_loading_enable_or') : tt('campcreate.pick_a_tile_then_set_the')}</p>
    </section>
    <section><h3>${tt('campcreate.campaign_objects')}</h3><div class="cmcreategrid">
      <button onclick="cmapCreateObject('fort')">${tt('campcreate.fort')}</button>
      <button onclick="cmapCreateObject('watchtower')">${tt('campcreate.watchtower')}</button>
      <button onclick="cmapCreateObject('resource')">${tt('campcreate.resource')}</button>
      <button onclick="cmapObjectMode()">${tt('campcreate.select_move_objects')}</button>
    </div><p>${tt('campcreate.click_an_icon_to_open_its')}</p></section>
  </div>`;
  // The displayed default must also be the value used by the placement action.
  if(faction && factions[faction]) c.createFaction = faction;
}

function cmapCreateStopPaint(){
  cpinCancel();
  if(state.cpaint && state.cpaint.on) cpaintToggle();
}

async function cmapCreateRegion(){
  const c = state.cmap, p = state.cpaint;
  if(!c || !p || p.busy) return;
  cpinCancel();
  if(!p.on) cpaintToggle();
  cmapSub('paint','brush');
  if(!p.on) return; // A campaign with private map files cannot paint base layers.
  if(!p.pal) await cpaintLoadPalette();
  if(state.cmap !== c || state.cpaint !== p || !p.pal) return;
  await cpaintWizOpen();
}

function cmapCreateMarker(kind){
  const c = state.cmap, p = state.cpaint;
  if(!c || !p || p.busy) return;
  const region = c.sel && c.sel.name ? c.sel.name : p.st.new_region && p.st.new_region.name;
  if(!region){ toast(tt('campcreate.select_a_region_first_then_choose'),5000); return; }
  if(c.man.campaign_map && c.man.campaign_map.paints === false){
    toast(tt('campcreate.this_campaign_uses_its_own_map'),6000); return;
  }
  cmapCreateStopPaint();
  cpinArm(tt('campcreate.the_for',{kind,region}), 'cmapCreateMarkerAt', [kind, region]);
}

async function cmapCreateMarkerAt(kind, region, game, tile){
  const c = state.cmap, p = state.cpaint;
  if(!c || !p || p.busy) return;
  const result = await cpaintPost('paint', {tool:'pencil',target:'regions',size:1,
    shape:'round',points:[tile],marker:kind,region,sea:false});
  if(!result || state.cmap !== c) return;
  if(result.error){ toast(result.error,7000); cpaintPaint(); return; }
  cpaintApply(result.changed);
  if(p.st.new_region) cpaintProgress();
  cpaintPaint();
  toast(tt('campcreate.marker_placed_review_save_to_write',{kind:kind === 'port' ? tt('campcreate.port') : tt('common.settlement')}),5000);
}

/* ---------- 96c: the port and the capital, by icon ----------

   Four icons in the region editor's "On the map" block: move the settlement,
   add a port, move the port, remove the port. A move places the new pixel
   first, through the same paint call and the same placement checks as the
   toolbar's marker button, and only then takes the old one off (the server's
   `erase_marker`), so a refused tile leaves the map as it was. That order is
   also the one-port rule: a region with a port is never offered Add, and a
   move ends with exactly one. Nothing is written to disk until Review & save,
   and each step is a stroke Undo takes back. */

//: The region the editor is open on, from the manifest, whose marker
//: positions the server brings up to date after every stroke.
function cmapMarkerRegion(){
  const c = state.cmap;
  const name = c && c.sel && c.sel.name;
  return name ? c.man.regions.find(r => r.name === name) || null : null;
}

function cmapMarkerReady(){
  const c = state.cmap, p = state.cpaint;
  if(!c || !p || p.busy) return false;
  if(c.man.campaign_map && c.man.campaign_map.paints === false){
    toast(tt('campcreate.this_campaign_uses_its_own_map'), 6000); return false;
  }
  return true;
}

function cmapMarkerMove(kind){
  const r = cmapMarkerRegion();
  if(!r || !cmapMarkerReady()) return;
  const old = kind === 'port' ? r.port : r.settlement;
  cmapCreateStopPaint();
  cpinArm(old ? tt('campcreate.the_new_place_for_s',{name:r.name,kind}) : tt('campcreate.s_new_port',{name:r.name}),
          'cmapMarkerMoveAt', [kind, r.name, old ? old.slice() : null]);
}

async function cmapMarkerMoveAt(kind, region, old, game, tile){
  const c = state.cmap, p = state.cpaint;
  if(!c || !p || p.busy) return;
  if(old && old[0] === tile[0] && old[1] === tile[1]) return;
  const placed = await cpaintPost('paint', {tool: 'pencil', target: 'regions', size: 1,
    shape: 'round', points: [tile], marker: kind, region, sea: false});
  if(!placed || state.cmap !== c) return;
  if(placed.error){ toast(placed.error, 7000); cpaintPaint(); return; }
  cpaintApply(placed.changed);
  if(old){
    const gone = await cpaintPost('paint', {tool: 'pencil', target: 'regions',
      points: [old], erase_marker: kind, region});
    if(!gone || state.cmap !== c) return;
    if(gone.error){
      toast(tt('campcreate.the_new_is_placed_but_the',{kind,error:gone.error}), 8000);
      cpaintPaint(); return;
    }
    cpaintApply(gone.changed);
  }
  cpaintPaint();
  cmapPickPaint();          // the icons follow: Add once the port is off
  toast(old ? tt('campcreate.s_moved_review_save_writes_it',{region,kind})
            : tt('campcreate.has_a_port_review_save_writes',{region}), 5000);
}

async function cmapMarkerRemove(kind){
  const r = cmapMarkerRegion();
  if(!r || !cmapMarkerReady()) return;
  const at = kind === 'port' ? r.port : r.settlement;
  if(!at) return;
  if(!confirm(tt('campcreate.take_s_off_the_map_review',{name:r.name,kind}))) return;
  const c = state.cmap;
  const gone = await cpaintPost('paint', {tool: 'pencil', target: 'regions',
    points: [at], erase_marker: kind, region: r.name});
  if(!gone || state.cmap !== c) return;
  if(gone.error){ toast(gone.error, 7000); cpaintPaint(); return; }
  cpaintApply(gone.changed);
  cpaintPaint();
  cmapPickPaint();          // the icons follow: Add once the port is off
}

//: The four icons, for the region editor's "On the map" block.
function cmapMarkerIconsHtml(){
  const r = cmapMarkerRegion();
  if(!r || !state.cpaint) return '';
  return `<div class="cmmarkicons">
    <button onclick="cmapMarkerMove('settlement')" ${r.settlement ? '' : 'disabled'}
      title="${ttA('campcreate.move_this_regions_settlement_click_the')}">${tt('campcreate.move_settlement')}</button>
    ${r.port ? `<button onclick="cmapMarkerMove('port')"
      title="${ttA('campcreate.move_this_regions_port_click_the')}">${tt('campcreate.move_port')}</button>
    <button onclick="cmapMarkerRemove('port')" title="${ttA('campcreate.take_this_regions_port_off_the')}">${tt('campcreate.remove_port')}</button>`
    : `<button onclick="cmapMarkerMove('port')"
      title="${ttA('campcreate.give_this_region_a_port_click')}">${tt('campcreate.add_port')}</button>`}
  </div>`;
}

async function cmapCreateSettlement(){
  const c = state.cmap, r = c && c.sel;
  if(!r || !r.name){ toast(tt('campcreate.select_a_region_to_edit_its'),4000); return; }
  cmapCreateStopPaint();
  await csOpen(r.name);
  if(state.cmap !== c) return;
  if(state.cset){ state.cset.open = true; csPaint(); }
  cmapSub('place','settle');
}

function cmapCreateCharacter(){
  const c = state.cmap;
  if(!c || !c.createFaction){ toast(tt('campcreate.choose_a_faction_for_the_new'),4000); return; }
  cmapCreateStopPaint();
  cpinArm(tt('campcreate.the_new_character'), 'cmapCreateCharacterAt', [c.createFaction,c.createType || 'general']);
}

//: 72, D13: the People panel's Horde start tab, for the chosen faction.
async function cmapCreateHorde(){
  const c = state.cmap;
  if(!c || !c.createFaction){ toast(tt('campcreate.choose_a_faction_for_the_horde'),4000); return; }
  cmapCreateStopPaint();
  await cxOpen(c.createFaction);
  const k = state.cx;
  if(state.cmap !== c || !k || k.faction !== c.createFaction) return;
  k.open = true;
  cxTab('horde');
  cmapSub('place','chars');
}

async function cmapCreateCharacterAt(faction, type, game){
  const c = state.cmap, campaign = c.campaign;
  const request = c.objectRequest = (c.objectRequest || 0) + 1;
  await cxOpen(faction);
  const k = state.cx;
  if(state.cmap !== c || c.campaign !== campaign || c.objectRequest !== request) return;
  if(!k || k.faction !== faction || !k.d){ toast(tt('campcreate.could_not_load_that_factions_character'),5000); return; }
  cxAdd();
  k.open = true; k.tab = 'people';
  Object.assign(k.w, {x:game[0],y:game[1],type,
    gender:type === 'princess' || type === 'witch' ? 'female' : 'male'});
  cxPaint(); cxPlanSoon(); cmapSub('place','chars');
}

async function cmapCreateObject(kind){
  const c = state.cmap;
  if(!c) return;
  const campaign = c.campaign;
  cmapCreateStopPaint(); cftOpen();
  if(!state.cft.d) await cftLoad();
  if(state.cmap !== c || c.campaign !== campaign) return;
  if(!state.cft || !state.cft.d){ toast(tt('campcreate.could_not_load_campaign_objects'),5000); return; }
  cpinArm(tt('campcreate.the_new',{kind}), 'cmapCreateObjectAt', [kind]);
}

function cmapCreateObjectAt(kind, game){
  cftPlace(kind,game);
  cmapSub('place','forts');
}

function cmapObjectMode(){
  cmapCreateStopPaint();
  state.cmap.selectMode = false;
  if(state.cmk && !state.cmk.on) cmkToggleLayer();
  cmapSub('paint','marks'); cpaintBarPaint();
  toast(tt('campcreate.click_an_object_to_edit_it'),5000);
}

// Claim object clicks before region picking can asynchronously open its owner's
// characters. This also works for an admiral standing on an unowned sea tile.
function cmapObjectPick(tile){
  if(!state.cmap || state.cmap.selectMode) return false;
  if(!cmapIconsOn()) return false;              // 97c: nothing drawn, nothing to click
  const items = cmkAt(tile[0],tile[1]).filter(it =>
    ['character','fort','watchtower','resource'].includes(it.kind));
  const item = items[items.length - 1];
  if(!item) return false;
  state.cmap.pick = tile.slice();
  state.cmap.lab = null;
  if(items.length > 1){
    state.cmap.objectSel = null;
    state.cmap.objectRequest = (state.cmap.objectRequest || 0) + 1;
    state.cmk.open = true; cmkPaint(); cmapSub('paint','marks');
    return true;
  }
  state.cmap.objectSel = item;
  cmapPaint();
  cmapObjectOpen(item);
  return true;
}

function cmapObjectChoose(index){
  const c = state.cmap;
  if(!c || !c.pick) return;
  const item = cmkAt(...c.pick).filter(it => ['character','fort','watchtower','resource'].includes(it.kind))[index];
  if(!item) return;
  c.objectSel = item; c.lab = null;
  cmapPaint(); cmapObjectOpen(item);
}

async function cmapObjectOpen(item){
  const c = state.cmap, campaign = c.campaign;
  const request = c.objectRequest = (c.objectRequest || 0) + 1;
  if(item.kind === 'character'){
    await cxOpen(item.faction);
    if(state.cmap !== c || c.campaign !== campaign || c.objectRequest !== request) return;
    const k = state.cx;
    if(!k || !k.d || k.faction !== item.faction) return;
    const i = k.d.characters.findIndex(ch => ch.line === item.line || ch.name === item.name);
    if(i < 0) return;
    cxPick(i); k.open = true; k.tab = 'people'; cxPaint();
    cmapSub('place','chars');
  }else{
    cftOpen();
    if(!state.cft.d) await cftLoad();
    if(state.cmap !== c || c.campaign !== campaign || c.objectRequest !== request || !state.cft.d) return;
    const record = cftFind(item);
    if(!record) return;
    state.cft.open = true; cftSelect(record); cmapSub('place','forts');
  }
}
