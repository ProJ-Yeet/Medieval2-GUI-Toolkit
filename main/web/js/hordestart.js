/* hordestart.js - Campaign Map: a horde start for a faction that holds nothing

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE HORDE START TAB - Phase 72, D13.

   Every name here starts `hs`, and there was no `hs` name anywhere in the
   tree before this phase.

   IT IS A TAB OF THE CAMPAIGN PANEL, beside New faction, because it is the
   other half of it: New faction writes a block with a purse and nothing in
   it, and says it will not appear on the map. This is what makes it appear.
   stratcamp.js draws the tab strip and hands the body of this tab here.

   TWO STARTS, ONE FORM. "On the map" writes a general per start, each with an
   army, into the faction's descr_strat block. "On a date" leaves it dormant
   and writes an emergent_faction event with its text and picture. Both write
   the horde itself - seven numbers and a unit list - into descr_sm_factions.
   The numbers are copied from a horde the mod already has when it has one.

   PYTHON OWNS THE RULES, as on every tab of this panel. A tile at sea, a name
   outside the pool, a stack of 21, a missing event picture: each comes back
   from /api/map/horde_plan as a sentence, on the same 450 ms debounce.
   ===================================================================== */

function hsNew(mod, campaign){
  return {mod, campaign, d: null, w: null, faction: '', loading: false,
          err: '', preview: null, timer: 0, busy: false};
}

async function hsOpen(faction, force){
  const c = state.cmap;
  if(!c) return;
  const was = state.hs;
  const same = was && was.mod === c.mod && was.campaign === (c.campaign || '');
  if(same && was.d && !force && (faction === undefined || faction === was.faction)){
    cjPaint(); return;
  }
  const k = state.hs = hsNew(c.mod, c.campaign || '');
  k.faction = faction !== undefined ? faction : (same ? was.faction : '');
  k.loading = true;
  cjPaint();
  let d;
  try{ d = await api.get(`/api/map/horde?mod=${enc(c.mod)}${cmapCampQ()}`
    + `&faction=${enc(k.faction)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.hs !== k) return;
  k.loading = false;
  if(d.error){ k.err = d.error; cjPaint(); return; }
  k.d = d;
  k.faction = d.faction ? d.faction.name : '';
  hsReset();
  cjPaint();
  hsPlanSoon();
}

/* The working copy, off what the faction already has: its own horde and its
   own event when it has them, else the mod's first horde's numbers, the units
   the EDU lets it own, and names out of its own pool. */
function hsReset(){
  const k = state.hs, f = k.d && k.d.faction;
  if(!f){ k.w = null; return; }
  const donor = (f.donors || [])[0];
  const whole = f.horde && Object.keys(f.horde.keys || {}).length === k.d.keys.length;
  const keys = Object.assign({}, k.d.defaults,
    whole ? f.horde.keys : donor ? donor.keys : {});
  const troops = (f.owned || []).filter(u => !(f.bodyguards || []).includes(u));
  const guard = (f.bodyguards || [])[0];
  k.w = {
    mode: (f.event || (f.flags || []).includes('dead_until_resurrected'))
      ? 'emerge' : 'map',
    donor: whole ? '' : donor ? donor.faction : '',
    keys,
    units: f.horde && f.horde.units.length ? f.horde.units.slice()
      : troops.slice(0, 6),
    generals: [{name: (f.names || [])[0] || '', age: k.d.default_age, x: '', y: '',
                army: (guard ? [guard] : []).concat(troops.slice(0, 3))}],
    dates: f.event ? f.event.dates.slice() : [''],
    positions: f.event ? f.event.positions.map(p => p.slice()) : [],
    title: f.text.title || '', text: f.text.body || '',
    picture_from: f.has_picture ? ''
      : ((f.pictures || []).includes('mongols') ? 'mongols'
         : (f.pictures || [])[0] || ''),
  };
}

function hsPick(name){ hsOpen(name, true); }

function hsSet(key, value){
  const k = state.hs;
  if(!k || !k.w) return;
  k.w[key] = value;
  hsPlanSoon();
  if(key === 'mode' || key === 'picture_from') cjPaint();
}

function hsKey(key, value){
  const k = state.hs;
  k.w.keys[key] = value;
  k.w.donor = '';
  hsPlanSoon();
}

//: The numbers of another horde in this mod, as they are - its units stay its own.
function hsDonor(slot){
  const k = state.hs, f = k.d.faction;
  const d = (f.donors || []).find(x => x.faction === slot);
  if(!d) return;
  k.w.keys = Object.assign({}, k.d.defaults, d.keys);
  k.w.donor = slot;
  hsPlanSoon();
  cjPaint();
}

/* ---- the lists: horde units, generals and their armies, dates, positions ---- */
function hsList(path){
  const k = state.hs;
  let at = k.w;
  for(let i = 0; i < path.length - 1; i++) at = at[path[i]];
  return [at, path[path.length - 1]];
}

function hsItem(path, value, repaint){
  const [at, key] = hsList(path);
  at[key] = value;
  hsPlanSoon();
  if(repaint) cjPaint();
}

function hsAdd(path, value){
  const [at, key] = hsList(path);
  at[key].push(value);
  hsPlanSoon();
  cjPaint();
}

function hsDrop(path, i){
  const [at, key] = hsList(path);
  at[key].splice(i, 1);
  hsPlanSoon();
  cjPaint();
}

function hsAddGeneral(){
  const k = state.hs, f = k.d.faction;
  const used = new Set(k.w.generals.map(g => g.name));
  const name = (f.names || []).find(n => !used.has(n)) || '';
  const last = k.w.generals[k.w.generals.length - 1];
  k.w.generals.push({name, age: k.d.default_age, x: '', y: '',
                     army: last ? last.army.slice() : []});
  hsPlanSoon();
  cjPaint();
}

//: The pin's answer: a general's tile, or a position (a new one when i is -1).
function hsPinned(kind, i, game){
  const k = state.hs;
  if(!k || !k.w){ toast('✗ the horde start was closed before the tile was picked',
    5000); return; }
  if(kind === 'gen'){
    const g = k.w.generals[i];
    if(!g) return;
    g.x = game[0]; g.y = game[1];
  } else if(i < 0 || !k.w.positions[i]) k.w.positions.push(game.slice());
  else k.w.positions[i] = game.slice();
  hsPlanSoon();
  cjPaint();
}

/* ---- the round trip ---- */
function hsBody(){
  const k = state.hs, w = k.w;
  const num = v => (String(v).trim() === '' ? '' : Number(v));
  const body = {mod: k.mod, campaign: k.d.campaign, faction: k.faction,
                mode: w.mode, keys: w.keys, units: w.units};
  if(w.mode === 'map')
    body.generals = w.generals.map(g => ({name: g.name, age: num(g.age),
      x: num(g.x), y: num(g.y), army: g.army}));
  else Object.assign(body, {dates: w.dates, positions: w.positions,
    title: w.title, text: w.text, picture_from: w.picture_from});
  return body;
}

function hsPlanSoon(){
  const k = state.hs;
  if(!k || !k.w) return;
  clearTimeout(k.timer);
  k.timer = setTimeout(() => hsPlanNow(k), CJ_DEBOUNCE);
}

async function hsPlanNow(k){
  if(state.hs !== k || !k.w) return;
  let res;
  try{ res = await api.post('/api/map/horde_plan', hsBody()); }
  catch(e){ res = {plan: {errors: [errText(e)], findings: [], changes: []}}; }
  if(state.hs !== k) return;
  k.preview = res.plan || null;
  cjPaint();
}

async function hsSave(){
  const k = state.hs;
  if(!k || !k.w || k.busy) return;
  clearTimeout(k.timer);
  const body = hsBody();
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/horde_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  const p = plan.plan || {};
  k.preview = p;
  cjPaint();
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const lines = (p.changes || []).slice(0, 16);
  const warn = (p.warnings || []).slice(0, 4).map(x => '⚠ ' + x);
  if(!confirm(`Write a horde start for ${k.faction} in ${k.d.campaign}?\n\n`
    + lines.join('\n')
    + ((p.changes || []).length > 16 ? `\n…and ${p.changes.length - 16} more` : '')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + `\n\n${(p.files || []).length} file(s), backed up first; one 🕑 Log undo `
    + 'puts every one of them back.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/horde_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  if(typeof fauStale === 'function') fauStale();
  activity('campaign', `${k.mod}: horde start (${body.mode}) for ${k.faction}`);
  const at = state.cmap && state.cmap.pick;
  await loadCampmap();
  if(at && state.cmap) cmapPick(at);
  hsOpen(k.faction, true);
}

/* ---------- drawing ---------- */

function hsHtml(){
  const k = state.hs;
  if(!k || k.loading) return '<div class="count">reading the faction…</div>';
  if(k.err) return `<div class="w-warn">${esc(k.err)}</div>`;
  const d = k.d, f = d.faction, w = k.w;
  const picker = `<div class="cmfield"><label>Faction</label>
    <select onchange="hsPick(this.value)">
      ${d.factions.map(x => `<option value="${esc(x.name)}"${
        f && x.name === f.name ? ' selected' : ''}>${esc(x.name)}${
        x.settlements ? ` - ${x.settlements} settlement(s)`
        : x.characters ? ` - ${x.characters} character(s)` : ' - holds nothing'}${
        x.dormant ? ', dormant' : ''}</option>`).join('')}
    </select>
    <div class="count">A horde start is for a faction with no settlement - the
      shape New faction writes, and vanilla's Mongols' and Timurids'.</div></div>`;
  if(!f || !w) return `<div class="cxform">${picker}</div>`;
  if(f.settlements.length) return `<div class="cxform">${picker}
    <div class="w-warn">${esc(f.name)} holds ${f.settlements.map(esc).join(', ')}.
      A horde start is the start of a faction with no home; the settlement
      panel gives a settlement to somebody else first.</div></div>`;
  return `<div class="cxform">
    ${picker}
    ${!f.in_sm ? `<div class="w-bad">descr_sm_factions.txt does not declare
      ${esc(f.name)} - the Factions screen clones the faction files first.</div>` : ''}
    <div class="cmfield"><label>How it starts</label>
      <label class="cjchk"><input type="radio" name="hsmode"${
        w.mode === 'map' ? ' checked' : ''} onchange="hsSet('mode','map')">On the
        map from turn one: its generals and their armies, written into its
        descr_strat.txt block</label>
      <label class="cjchk"><input type="radio" name="hsmode"${
        w.mode === 'emerge' ? ' checked' : ''} onchange="hsSet('mode','emerge')">On
        a date: dormant until an <code>emergent_faction</code> event brings it
        in, as vanilla's Mongols and Timurids do</label>
    </div>
    ${hsKeysHtml()}
    ${hsUnitsHtml()}
    ${w.mode === 'map' ? hsGeneralsHtml() : hsEventHtml()}
    <div class="csbtns">
      <button class="primary" onclick="hsSave()"${k.busy ? ' disabled' : ''}
        >Write the horde start</button>
      <button onclick="hsReset();hsPlanSoon();cjPaint()">Start over</button>
    </div>
    ${hsPlanHtml()}
    <datalist id="hsUnits">${(f.owned || []).concat(
      (f.units || []).filter(u => !(f.owned || []).includes(u))).map(u =>
      `<option value="${esc(u)}">`).join('')}</datalist>
    <datalist id="hsNames">${(f.names || []).map(n =>
      `<option value="${esc(n)}">`).join('')}</datalist>
  </div>`;
}

function hsKeysHtml(){
  const k = state.hs, f = k.d.faction, w = k.w;
  const donors = f.donors || [];
  return `<div class="cmfield"><label>The horde, in descr_sm_factions.txt</label>
    ${donors.length ? `<div class="csbtns">${donors.map(x =>
      `<button${w.donor === x.faction ? ' class="on"' : ''}
        onclick="hsDonor('${esc(x.faction)}')">${esc(x.faction)}'s numbers</button>`)
      .join('')}</div>`
      : `<div class="count">This mod has no horde to copy the numbers from, so
        these are the tool's own starting values.</div>`}
    <div class="csrow2">${k.d.keys.map(key => `<div class="cmfield">
      <label>${esc(key.replace(/^horde_/, '').replace(/_/g, ' '))}</label>
      <input type="number" min="0" value="${esc(String(w.keys[key] ?? ''))}"
        oninput="hsKey('${key}', this.value)"></div>`).join('')}</div>
  </div>`;
}

function hsUnitsHtml(){
  const w = state.hs.w;
  return `<div class="cmfield"><label>Horde units
    <span class="count">${w.units.length} - what it is made of; units this
      faction owns are offered first</span></label>
    <div class="cxlist">${w.units.map((u, i) => `<div class="cxrow">
      <input list="hsUnits" value="${esc(u)}"
        oninput="hsItem(['units', ${i}], this.value)">
      <button onclick="hsDrop(['units'], ${i})" title="Remove">✕</button>
    </div>`).join('') || '<div class="count">none</div>'}</div>
    <div class="csbtns"><button onclick="hsAdd(['units'], '')">＋ unit</button></div>
  </div>`;
}

function hsGeneralsHtml(){
  const k = state.hs, w = k.w, f = k.d.faction;
  return `<div class="cmfield"><label>Generals on the map
    <span class="count">${f.leader
      ? `${esc(f.leader)} already leads ${esc(f.name)}, so none of these does`
      : 'the first one leads the faction'}</span></label>
    ${w.generals.map((g, i) => `<div class="cxpanel">
      <div class="csrow2">
        <div class="cmfield"><label>Name</label>
          <input list="hsNames" value="${esc(g.name)}"
            oninput="hsItem(['generals', ${i}, 'name'], this.value)"></div>
        <div class="cmfield"><label>Age</label>
          <input type="number" min="0" value="${esc(String(g.age))}"
            oninput="hsItem(['generals', ${i}, 'age'], this.value)"></div>
      </div>
      <div class="cxrow">
        <input style="width:5.5em" placeholder="x" value="${esc(String(g.x))}"
          oninput="hsItem(['generals', ${i}, 'x'], this.value)">
        <input style="width:5.5em" placeholder="y" value="${esc(String(g.y))}"
          oninput="hsItem(['generals', ${i}, 'y'], this.value)">
        ${cpinButton(`${g.name || 'general ' + (i + 1)}'s tile`, 'hsPinned', ['gen', i])}
        ${w.generals.length > 1 ? `<button onclick="hsDrop(['generals'], ${i})"
          title="Remove this general">✕</button>` : ''}
      </div>
      <div class="cxlist">${g.army.map((u, j) => `<div class="cxrow">
        <input list="hsUnits" value="${esc(u)}"
          oninput="hsItem(['generals', ${i}, 'army', ${j}], this.value)">
        <button onclick="hsDrop(['generals', ${i}, 'army'], ${j})"
          title="Remove">✕</button></div>`).join('')}</div>
      <div class="csbtns"><button onclick="hsAdd(['generals', ${i}, 'army'], '')"
        >＋ unit <span class="count">${g.army.length} of ${k.d.stack_limit}</span>
        </button></div>
    </div>`).join('')}
    <div class="csbtns"><button onclick="hsAddGeneral()">＋ general</button></div>
    <div class="count">x and y as descr_strat.txt writes them, y up from the
      bottom. The people panel edits them afterwards like anybody else.</div>
  </div>`;
}

function hsEventHtml(){
  const k = state.hs, w = k.w, f = k.d.faction, size = k.d.size;
  const pos = w.positions.map((p, i) => {
    const off = size && !(p[0] >= 0 && p[1] >= 0 && p[0] < size[0] && p[1] < size[1]);
    return `<div class="cxrow">
      <input style="width:5.5em" value="${esc(String(p[0]))}"
        oninput="hsItem(['positions', ${i}, 0], Number(this.value))">
      <input style="width:5.5em" value="${esc(String(p[1]))}"
        oninput="hsItem(['positions', ${i}, 1], Number(this.value))">
      ${off ? `<span class="w-bad">off a ${size[0]}×${size[1]} map</span>`
            : '<span class="count">x, y</span>'}
      ${cpinButton(`position ${i + 1}`, 'hsPinned', ['pos', i])}
      <button onclick="hsDrop(['positions'], ${i})" title="Remove">✕</button>
    </div>`;
  }).join('');
  return `<div class="cmfield"><label>When
    <span class="count">a turn, or two it falls between - "100 110"</span></label>
    <div class="cxlist">${w.dates.map((d, i) => `<div class="cxrow">
      <input value="${esc(d)}" placeholder="100 110"
        oninput="hsItem(['dates', ${i}], this.value)">
      ${w.dates.length > 1 ? `<button onclick="hsDrop(['dates'], ${i})"
        title="Remove">✕</button>` : ''}</div>`).join('')}</div>
  </div>
  <div class="cmfield"><label>Where it comes in</label>
    <div class="cxlist">${pos || '<div class="count">none</div>'}</div>
    <div class="csbtns">${cpinButton('where the horde comes in', 'hsPinned', ['pos', -1])}
      <button onclick="hsAdd(['positions'], [0, 0])">＋ blank</button></div>
    <div class="count">Written as the event's <code>position</code> lines.
      Where the horde really lands is the first thing to check in game.</div>
  </div>
  <div class="cmfield"><label>What the player reads
    <span class="count">{${esc(f.name.toUpperCase())}_TITLE} and _BODY in
      text/historic_events.txt${f.text.have_file ? '' : ' - blank here means a default'}</span></label>
    <input value="${esc(w.title)}" placeholder="The ${esc(f.name)} arrive"
      oninput="hsSet('title', this.value)">
    <input value="${esc(w.text)}" placeholder="A horde has appeared on the map."
      oninput="hsSet('text', this.value)">
  </div>
  ${f.eventspic.length ? `<div class="cmfield"><label>Event picture</label>
    ${f.has_picture ? `<div class="count">Every eventspic folder already has
      ${esc(f.name)}.tga.</div>`
    : `<select onchange="hsSet('picture_from', this.value)">
        <option value="">(pick one)</option>
        ${(f.pictures || []).map(p => `<option value="${esc(p)}"${
          p === w.picture_from ? ' selected' : ''}>a copy of ${esc(p)}.tga</option>`)
          .join('')}</select>
      <div class="count">${f.eventspic.length} folder(s) need a ${esc(f.name)}.tga;
        a missing event picture crashes the campaign when the event fires.</div>`}
  </div>` : ''}`;
}

function hsPlanHtml(){
  const p = state.hs.preview;
  if(!p) return '';
  const errs = (p.errors || []).filter(e => e !== 'nothing to change');
  const warns = p.warnings || [];
  const blocks = Object.entries(p.blocks || {});
  return `<div class="cjplan">
    ${errs.map(e => `<div class="w-bad">${esc(e)}</div>`).join('')}
    ${warns.map(e => `<div class="w-warn">${esc(e)}</div>`).join('')}
    ${(p.changes || []).length ? `<div class="count">${
      p.changes.map(esc).join(' · ')}</div>` : ''}
    ${blocks.map(([rel, text]) => `<div class="count">${esc(rel)}</div>
      <pre class="cjblock">${esc(text)}</pre>`).join('')}
  </div>`;
}
