/* Campaign creation shortcuts reuse the existing validated editors and saves. */
function cmapCreatePaint(){
  const el = document.getElementById('cmCreate'), c = state.cmap;
  if(!el || !c) return;
  const k = state.cmk, factions = k && k.d ? k.d.factions || {} : {};
  const faction = c.createFaction || (c.sel && c.sel.faction) || '';
  const type = c.createType || 'general';
  el.innerHTML = `<div class="cmcreate">
    <div class="cmcreateintro"><b>Create on the map</b>
      <span>Choose what to add, then place it on a tile. Review its details before saving.</span></div>
    <section><h3>Regions &amp; settlements</h3><div class="cmcreategrid">
      <button class="primary" onclick="cmapCreateRegion()"><b>＋ New region</b><small>Name → paint → settlement → port</small></button>
      <button onclick="cmapCreateMarker('settlement')"><b>⌂ Settlement marker</b><small>Add or move on the selected region</small></button>
      <button onclick="cmapCreateMarker('port')"><b>⚓ Port marker</b><small>Add or move on the selected region</small></button>
      <button onclick="cmapCreateSettlement()"><b>▣ Settlement details</b><small>Owner, buildings &amp; level</small></button>
    </div><p>Select a region first for markers. Marker edits use Review &amp; save.</p></section>
    <section><h3>Characters &amp; armies</h3>
      <label>Faction<select aria-label="New character faction" onchange="state.cmap.createFaction=this.value">
        <option value="">Choose a faction…</option>${Object.entries(factions).map(([id,f]) =>
          `<option value="${esc(id)}"${id === faction ? ' selected' : ''}>${esc(f.label || id)}</option>`).join('')}
      </select></label>
      <label>Character type<select aria-label="New character type" onchange="state.cmap.createType=this.value">
        ${Object.keys(CMK_CHAR).map(t => `<option value="${esc(t)}"${t === type ? ' selected' : ''}>${esc(t)}</option>`).join('')}
      </select></label>
      <button onclick="cmapCreateCharacter()" ${Object.keys(factions).length ? '' : 'disabled'}>＋ Place character / army</button>
      <button onclick="cmapCreateHorde()" ${Object.keys(factions).length ? '' : 'disabled'}
        title="For a faction that holds nothing: leaders and armies on free land, or an event that raises it later">⚑ Horde start…</button>
      <p>${k && k.err ? esc(k.err) : !Object.keys(factions).length ? 'Campaign factions are loading. Enable or retry Map icons if loading fails.' : 'Pick a tile, then set the name, traits and army in the character editor.'}</p>
    </section>
    <section><h3>Campaign objects</h3><div class="cmcreategrid">
      <button onclick="cmapCreateObject('fort')">▣ Fort</button>
      <button onclick="cmapCreateObject('watchtower')">♜ Watchtower</button>
      <button onclick="cmapCreateObject('resource')">◆ Resource</button>
      <button onclick="cmapObjectMode()">⌖ Select / move objects</button>
    </div><p>Click an icon to open its editor. Drag movable objects to preview a new position.</p></section>
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
  if(!region){ toast('Select a region first, then choose its settlement or port marker.',5000); return; }
  if(c.man.campaign_map && c.man.campaign_map.paints === false){
    toast('This campaign uses its own map. Open a campaign using the base map to edit markers.',6000); return;
  }
  cmapCreateStopPaint();
  cpinArm(`the ${kind} for ${region}`, 'cmapCreateMarkerAt', [kind, region]);
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
  toast(`${kind === 'port' ? 'Port' : 'Settlement'} marker placed. Review & save to write the map.`,5000);
}

async function cmapCreateSettlement(){
  const c = state.cmap, r = c && c.sel;
  if(!r || !r.name){ toast('Select a region to edit its settlement.',4000); return; }
  cmapCreateStopPaint();
  await csOpen(r.name);
  if(state.cmap !== c) return;
  if(state.cset){ state.cset.open = true; csPaint(); }
  cmapSub('place','settle');
}

function cmapCreateCharacter(){
  const c = state.cmap;
  if(!c || !c.createFaction){ toast('Choose a faction for the new character.',4000); return; }
  cmapCreateStopPaint();
  cpinArm('the new character', 'cmapCreateCharacterAt', [c.createFaction,c.createType || 'general']);
}

//: 72, D13: the People panel's Horde start tab, for the chosen faction.
async function cmapCreateHorde(){
  const c = state.cmap;
  if(!c || !c.createFaction){ toast('Choose a faction for the horde start.',4000); return; }
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
  if(!k || k.faction !== faction || !k.d){ toast('Could not load that faction’s character editor.',5000); return; }
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
  if(!state.cft || !state.cft.d){ toast('Could not load campaign objects.',5000); return; }
  cpinArm(`the new ${kind}`, 'cmapCreateObjectAt', [kind]);
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
  toast('Click an object to edit it. Drag characters, forts, watchtowers or resources to move them.',5000);
}

// Claim object clicks before region picking can asynchronously open its owner's
// characters. This also works for an admiral standing on an unowned sea tile.
function cmapObjectPick(tile){
  if(!state.cmap || state.cmap.selectMode) return false;
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
