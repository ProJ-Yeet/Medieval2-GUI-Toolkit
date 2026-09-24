/* hordestart.js - Campaign Map: a horde start for a faction that holds nothing

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   PHASE 72, D13 - the Campaign panel's seventh tab.

   Every name here starts `hs`, and there was no `hs` name anywhere in the
   tree before this phase - checked.

   New faction, the tab beside this one, makes a faction with no settlement and
   nobody in it, which is the shape vanilla's Mongols are. This tab is the other
   half: the armies it arrives with, on the turn it arrives. The server writes
   them as ONE monitor in the campaign script, between two marker comments,
   and gives the faction `dead_until_resurrected` - one plan, one Undo, and no
   line of the script outside the markers is ever touched. The markers are what
   let this tab open a start it wrote and change it or take it out again.

   PYTHON OWNS THE RULES, as everywhere on this panel: whether a tile is
   impassable, whether a unit is in the EDU, whether a name is in the faction's
   pool all come back from `hordestart.check_armies` as sentences. The form asks
   on the same debounce 16j uses.
   ===================================================================== */

function hsBlankArmy(){
  const c = state.cmap;
  const at = (c && c.pick) || [0, 0];
  return {name: '', type: 'named character', age: 30,
          x: at[0], y: c && c.man ? c.man.height - 1 - at[1] : 0,
          units: [{unit: '', exp: 0, armour: 0, weapon_lvl: 0}]};
}

async function hsOpen(force){
  const k = state.cj;
  if(!k || !k.d) return;
  if(k.hs && !force){ cjPaint(); return; }
  k.hs = {loading: true, d: null, err: '', pick: '', w: null, flag: true};
  cjPaint();
  let d;
  try{ d = await api.get(`/api/map/horde?mod=${enc(k.mod)}`
    + `&campaign=${enc(k.d.campaign)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cj !== k || !k.hs) return;
  k.hs.loading = false;
  if(d.error){ k.hs.err = d.error; cjPaint(); return; }
  k.hs.d = d;
  const first = d.factions.find(f => f.start) || d.factions.find(f => f.homeless)
    || d.factions[0] || {};
  hsPick(first.name || '');
}

function hsPick(name){
  const k = state.cj, h = k && k.hs;
  if(!h || !h.d) return;
  h.pick = name;
  const f = h.d.factions.find(x => x.name === name) || {};
  h.w = f.start ? JSON.parse(JSON.stringify({turn: f.start.turn,
                                             armies: f.start.armies}))
                : {turn: 0, armies: [hsBlankArmy()]};
  k.preview = null;
  cjPaint();
  hsPlanSoon();
}

function hsSet(path, value){
  const h = state.cj && state.cj.hs;
  if(!h || !h.w) return;
  // path: ['turn'] or ['armies', i, key] or ['armies', i, 'units', j, key]
  let o = h.w;
  for(let i = 0; i < path.length - 1; i++) o = o[path[i]];
  o[path[path.length - 1]] = value;
  hsPlanSoon();
}

function hsArmy(add, i){
  const h = state.cj.hs;
  if(add) h.w.armies.push(hsBlankArmy()); else h.w.armies.splice(i, 1);
  cjPaint(); hsPlanSoon();
}

function hsUnit(i, add, j){
  const a = state.cj.hs.w.armies[i];
  if(add) a.units.push({unit: '', exp: 0, armour: 0, weapon_lvl: 0});
  else a.units.splice(j, 1);
  cjPaint(); hsPlanSoon();
}

//: The tile the map is looking at, flipped into game coordinates - the same
//: transform the people panel's Here button makes.
function hsHere(i){
  const c = state.cmap, a = state.cj.hs.w.armies[i];
  if(!c || !c.pick){ toast('Click a tile on the map first', 4000); return; }
  a.x = c.pick[0];
  a.y = c.man.height - 1 - c.pick[1];
  cjPaint(); hsPlanSoon();
}

function hsBody(extra){
  const k = state.cj, h = k.hs;
  return Object.assign({mod: k.mod, campaign: k.d.campaign, faction: h.pick,
                        action: 'write', turn: h.w.turn, armies: h.w.armies,
                        flag: h.flag, sig: h.d.sig}, extra || {});
}

function hsPlanSoon(){
  const k = state.cj;
  if(!k || !k.hs || !k.hs.w) return;
  clearTimeout(k.timer);
  k.timer = setTimeout(() => hsPlanNow(k), CJ_DEBOUNCE);
}

async function hsPlanNow(k){
  if(state.cj !== k || !k.hs || !k.hs.w || k.tab !== 'horde') return;
  let res;
  try{ res = await api.post('/api/map/horde_plan', hsBody()); }
  catch(e){ res = {plan: {errors: [errText(e)], findings: [], changes: []}}; }
  if(state.cj !== k) return;
  k.preview = res.plan || null;
  cjPaint();
}

async function hsSave(action){
  const k = state.cj, h = k && k.hs;
  if(!h || !h.w || k.busy) return;
  clearTimeout(k.timer);
  const body = hsBody({action});
  k.busy = true;
  let plan;
  try{ plan = await api.post('/api/map/horde_plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); k.preview = plan.plan || null;
    cjPaint(); return; }
  const p = plan.plan || {};
  k.preview = p;
  cjPaint();
  const warn = (p.warnings || []).slice(0, 5).map(x => '⚠ ' + x);
  if(!confirm(`${action === 'remove' ? 'Remove' : 'Write'} the horde start for `
    + `${h.pick} in ${k.d.campaign}?\n\n`
    + ((p.changes || []).join('\n') || 'no visible change')
    + (warn.length ? '\n\n' + warn.join('\n') : '')
    + `\n\nFiles: ${(p.files || []).join(', ')}`
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  k.busy = true;
  let res;
  try{ res = await api.post('/api/map/horde_apply', body); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  activity('campaign', `${k.mod}: horde start ${action} ${h.pick}`);
  const pick = h.pick;
  await hsOpen(true);
  if(state.cj && state.cj.hs && pick) hsPick(pick);
}

function hsHtml(){
  const k = state.cj, h = k.hs;
  if(!h || h.loading) return '<div class="count">reading the campaign script…</div>';
  if(h.err) return `<div class="w-warn">${esc(h.err)}</div>`;
  const d = h.d;
  const rows = d.factions.map(f => `<div class="cxrow${f.name === h.pick ? ' on' : ''}"
      onclick="hsPick('${esc(f.name)}')">
      <b>${esc(f.name)}</b>
      <span class="count">${f.homeless ? 'holds nothing'
        : `${f.settlements} settlement(s), ${f.characters} character(s)`}${
        f.flags.length ? ' · ' + f.flags.map(esc).join(', ') : ''}${
        f.start ? ` · horde start on turn ${f.start.turn}, ${f.start.armies.length} army(ies)` : ''}${
        f.scripted > 0 ? ` · ${f.scripted} other scripted spawn(s)` : ''}</span>
    </div>`).join('');
  const f = d.factions.find(x => x.name === h.pick) || {};
  return `<div class="cxform">
    <div class="count hswrap">Script: ${esc(d.script)}${d.exists ? ''
      : ' - not there yet; a save writes it'}.</div>
    ${d.error ? `<div class="w-bad">${esc(d.error)}</div>` : ''}
    <div class="cxlist">${rows}</div>
    ${h.w && !d.error ? hsFormHtml(f) : ''}
  </div>`;
}

function hsFormHtml(f){
  const k = state.cj, h = k.hs, d = h.d, w = h.w;
  const pool = (d.pool || {})[h.pick] || [];
  const armies = w.armies.map((a, i) => `<div class="cjplan">
    <div class="cshead"><b>Army ${i + 1}</b>
      ${w.armies.length > 1 ? `<button onclick="hsArmy(false, ${i})">Remove</button>` : ''}</div>
    <div class="csrow2">
      <div class="cmfield"><label>Led by</label>
        <input list="hsl-pool" value="${esc(a.name)}" placeholder="Hulagu"
          oninput="hsSet(['armies', ${i}, 'name'], this.value)"></div>
      <div class="cmfield"><label>Who</label>
        <select onchange="hsSet(['armies', ${i}, 'type'], this.value)">
          ${d.types.map(t => `<option${t === a.type ? ' selected' : ''}>${t}</option>`).join('')}
        </select></div>
    </div>
    <div class="cmfield"><label>Age, then the tile (x, y)</label>
      <div class="hsline">
        <input type="number" min="0" value="${esc(a.age)}" title="age"
          oninput="hsSet(['armies', ${i}, 'age'], this.value)">
        <input type="number" value="${esc(a.x)}" title="x"
          oninput="hsSet(['armies', ${i}, 'x'], this.value)">
        <input type="number" value="${esc(a.y)}" title="y, counted up from the bottom as the file does"
          oninput="hsSet(['armies', ${i}, 'y'], this.value)">
        <button onclick="hsHere(${i})" title="The tile picked on the map">Here</button>
      </div></div>
    <div class="count">Regiments: unit, then exp, armour, weapon_lvl.</div>
    ${a.units.map((u, j) => `<div class="hsunit">
      <input list="hsl-unit" value="${esc(u.unit)}" placeholder="unit"
        oninput="hsSet(['armies', ${i}, 'units', ${j}, 'unit'], this.value)">
      <div class="hsline">
      ${['exp', 'armour', 'weapon_lvl'].map(n => `<input type="number" min="0"
        title="${n}" value="${esc(u[n])}"
        oninput="hsSet(['armies', ${i}, 'units', ${j}, '${n}'], this.value)">`).join('')}
      <button onclick="hsUnit(${i}, false, ${j})" title="Take this regiment out">✕</button>
      </div>
    </div>`).join('')}
    <button onclick="hsUnit(${i}, true)"${a.units.length >= d.stack ? ' disabled' : ''}
      >+ regiment</button>
    <span class="count">${a.units.length} of ${d.stack}</span>
  </div>`).join('');
  return `
    <div class="cshead"><b>${esc(h.pick)}</b>
      <span class="count">${f.start ? 'its horde start, as written' : 'a new horde start'}</span></div>
    <div class="cmfield"><label>Turn</label>
      <input type="number" min="0" value="${esc(w.turn)}"
        oninput="hsSet(['turn'], this.value)">
      <div class="count">As the script counts it: I_TurnNumber, the first
        turn is 0. It fires on the rebels' turn, once.</div></div>
    <label class="cjchk"><input type="checkbox"${h.flag ? ' checked' : ''}
      onchange="state.cj.hs.flag = this.checked; hsPlanSoon()">
      Give it dead_until_resurrected</label>
    <div class="count">So a faction that holds nothing is not counted destroyed
      before it arrives. Only added when it holds nothing and lacks it.</div>
    ${f.horde_keys ? '' : `<div class="count">descr_sm_factions.txt gives
      ${esc(h.pick)} no horde_ settings; the Factions screen edits them.</div>`}
    ${armies}
    <datalist id="hsl-pool">${pool.map(n => `<option value="${esc(n)}">`).join('')}</datalist>
    <datalist id="hsl-unit">${(d.units || []).map(u =>
      `<option value="${esc(u.name)}">${u.general ? 'bodyguard' : ''}</option>`).join('')}</datalist>
    <div class="csbtns">
      <button onclick="hsArmy(true)">+ army</button>
      <button class="primary" onclick="hsSave('write')">${f.start
        ? 'Save the horde start' : 'Write the horde start'}</button>
      ${f.start ? `<button onclick="hsSave('remove')">Remove it</button>` : ''}
    </div>`;
}
