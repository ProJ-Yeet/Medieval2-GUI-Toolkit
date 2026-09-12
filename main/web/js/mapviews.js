/* mapviews.js - Campaign Map: named views, saved and loaded

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   NAMED VIEW PRESETS - Phase 20b, T9.

   Every name here starts `cvw`, and none of them existed anywhere else in the
   tree before this phase. Not `cv`: that is what half this codebase calls a
   <canvas> local, and a top-level `cvSave` beside forty `const cv =` lines is
   a name that reads wrong even when it works.

   THE SAME STORE, KEYED BY A NAME. 16d already remembers one layer stack in
   `map_layers` on /api/settings, and it already does the hard part: a saved
   draw order is a list of codes written by an older run of the tool, so it is
   reconciled against the manifest rather than trusted - codes that are still
   real keep their saved place, anything new goes where the server put it,
   nothing is dropped or invented. That is `cmapOrder`, it was built in 16d,
   and this file is that store with a name on it and a picker over it.

   WHAT A VIEW IS, AND WHAT IT DELIBERATELY IS NOT. It is everything that
   changes what the map LOOKS like: which layers are drawn, in what order, at
   what opacity, with which colours punched out of each, 20a's two readings of
   a layer (the rivers lifted out of the features layer, the heights drawn as
   transparency) and 16g's colouring over the top. It is not the view itself -
   no zoom, no pan, no selection - and it is not the tooltip. A place is not a
   habit: 16d's own ruling about what `map_layers` keeps applies here whole, and
   a preset that jumped the map somewhere would be a preset nobody could use
   twice on two mods.

   THE PLAN IS PURE, THE APPLY IS NOT. `cvwPlan` takes a manifest and a saved
   preset and returns what to do about it, including what it had to drop and
   what the manifest has that the preset never saw. Nothing in it touches the
   screen, which is what lets `tests/test_mapgo.py` reconcile a preset written
   against a ten-layer map onto a manifest with nine, in node, on the real
   function.
   ===================================================================== */

//: How many presets are kept. There is no cost to another one, but a picker
//: with forty entries is a picker you scroll instead of read - and the nine
//: `.mps` files TWMapReader's own author shipped beside it are the measured
//: size of a working set.
const CVW_MAX = 24;

//: What one is called when nobody says. Numbered rather than "Untitled",
//: because two Untitleds is the state this exists to avoid.
const CVW_NAME = 'View';

/* ---------- state ----------

   The presets themselves live in `state.settings.map_views` - the same
   settings object `map_layers` is in, saved by the same route - so this state
   is only what the panel is doing: whether it is open, and the one refusal it
   can have to show. */
function cvwNew(mod){
  return {mod, open: false, err: ''};
}

function cvwOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cvw || state.cvw.mod !== c.mod) state.cvw = cvwNew(c.mod);
  cvwPaint();
}

function cvwToggle(){
  const k = state.cvw;
  if(!k) return;
  k.open = !k.open;
  activity('map views', k.open ? 'opened the saved views' : 'closed the saved views');
  cvwPaint();
}

/* Every saved view, as an array, from the settings object the page already has.

   Defensive about its own shape for the reason `cmapSettings` is: this comes
   out of a JSON file a person can edit, and an entry that is not an object with
   a name is dropped rather than drawn as a blank row. */
function cvwList(){
  const s = state.settings || (state.settings = {});
  if(!Array.isArray(s.map_views)) s.map_views = [];
  s.map_views = s.map_views.filter(v => v && typeof v === 'object' && v.name);
  return s.map_views;
}

//: Coalesced like `cmapSaveLayers`, and for the same reason: renaming an entry
//: types one character at a time and settings.json is rewritten whole.
let cvwSaveTimer = 0;
function cvwStore(){
  const list = cvwList();
  clearTimeout(cvwSaveTimer);
  cvwSaveTimer = setTimeout(() => {
    try{ api.post('/api/settings', {map_views: list}); }catch(e){}
  }, 300);
}

/* ---------- taking a view, and putting one back ---------- */

/* The screen as a preset.

   `cmapLayerState` is the same snapshot `cmapSaveLayers` writes into
   `map_layers`, which is the point of the whole item - there is one description
   of what the layer stack is, and a preset is a copy of it with a name. The
   colouring is added here because it belongs to the query panel rather than to
   the layer stack, and it is stored as the theme's CODE: the colours themselves
   are the server's answer about this mod, and a preset that carried them would
   paint another mod's provinces with them. */
function cvwSnapshot(name){
  const snap = cmapLayerState();
  delete snap.tip;                    // a habit about the pointer, not a view
  const q = state.cq;
  return Object.assign({name: String(name || '').trim() || CVW_NAME}, snap, {
    theme: (q && q.theme) || '',
    theme_opacity: q ? q.opacity : 0.85,
    theme_borders: q ? !!q.borders : true,
  });
}

/* What loading this preset would do to this map. Pure.

   Three things can be true of a saved preset and all three are ordinary. A
   layer it names may not be in this manifest (an older build, a renamed code);
   a layer in the manifest may be one the preset never saw; and a hidden colour
   in it may be a colour that only existed on another mod's map. The first two
   are `cmapOrder`'s job and it has done it since 16d. The third is reported
   rather than fixed - a punched colour that matches nothing punches nothing,
   and the row saying so is more use than a silent tidy-up. */
function cvwPlan(man, preset){
  const p = preset || {};
  // Three of its fields are tables and one is a list, and every one of them
  // comes out of settings.json - which is a file a person can open and a
  // build can change the shape of. Anything that is not the shape this reads
  // is treated as absent, which lands on the manifest's own defaults below.
  const table = v => (v && typeof v === 'object' && !Array.isArray(v)) ? v : {};
  const on0 = table(p.on), op0 = table(p.opacity), hide0 = table(p.hide);
  const real = (man.layers || []).map(l => l.code);
  const order = cmapOrder(man, p.order);
  const layers = {};
  for(const code of real){
    const def = man.layers.find(l => l.code === code) || {};
    const want = (code in on0) ? !!on0[code] : !!def.on;
    const op = typeof op0[code] === 'number'
      ? op0[code] : (typeof def.opacity === 'number' ? def.opacity : 1);
    const hide = Array.isArray(hide0[code]) ? hide0[code].slice()
      : (def.blank ? [def.blank.key] : []);
    layers[code] = {on: want && def.present !== false,
                    opacity: Math.max(0, Math.min(1, op)),
                    hide};
  }
  const named = Object.keys(on0).concat(Array.isArray(p.order) ? p.order : []);
  return {
    order, layers,
    rivers: !!(p.river && p.river.on),
    riverRgb: (p.river && Array.isArray(p.river.rgb) && p.river.rgb.length === 3
               && p.river.rgb.every(v => typeof v === 'number'))
      ? p.river.rgb.slice() : CMAP_RIVER_RGB.slice(),
    heightAlpha: !!p.height_alpha,
    // 23a: the terrain composite. A preset saved before it has no word on it
    // and opens without it, which is what that view looked like when it was
    // saved - the same reading 20c's names get two lines down.
    terrain: !!p.terrain,
    // 20c, T4. A preset saved before 20c has no word on it and opens without
    // names, which is what that view looked like when it was saved.
    labels: !!p.labels,
    theme: p.theme || '',
    themeOpacity: typeof p.theme_opacity === 'number' ? p.theme_opacity : 0.85,
    themeBorders: p.theme_borders !== false,
    //: layers the preset named that this map has not got, and the reverse
    dropped: [...new Set(named)].filter(code => !real.includes(code)).sort(),
    added: real.filter(code => !named.includes(code)),
  };
}

/* Load one. The only function here that touches the screen.

   Everything it changes goes through the functions that own it: the order and
   the per-layer values are written onto `state.cmap` exactly as `cmapNew`
   writes them at construction, then the mask pass is re-run for every layer
   whose reading changed and the composite is rebuilt once. `cmapLoadLayers`
   picks up any layer this preset ticked on that has never been fetched. */
function cvwLoad(i){
  const k = state.cvw, c = state.cmap, v = cvwList()[i];
  if(!k || !c || !v) return;
  const plan = cvwPlan(c.man, v);
  c.order = plan.order;
  for(const [code, want] of Object.entries(plan.layers)){
    const L = c.layers[code];
    if(!L) continue;
    L.on = want.on;
    L.opacity = want.opacity;
    L.hide = new Set(want.hide);
    L.maskKey = '';
  }
  c.rivers = plan.rivers;
  c.riverRgb = plan.riverRgb.slice();
  c.heightAlpha = plan.heightAlpha;
  c.terrain.on = plan.terrain;
  c.labels = plan.labels; c.lab = null; c.saidZoom = null;
  const lb = document.getElementById('cmLabBtn');
  if(lb) lb.classList.toggle('on', !!c.labels);
  for(const code of c.order) if(c.layers[code].img) cmapMask(c, code);
  cmapCompose(); cmapPaint(); cmapSaveLayers(); cmapRepanel();
  cmapLoadLayers();
  if(c.terrain.on) cmapTerrainLoad();
  // 16g's colouring, if the query panel is on this page at all. Applied last
  // because it is a request: the theme's table is the server's answer about
  // this mod, and everything above is already on screen by the time it lands.
  const q = state.cq;
  if(q && typeof cqTheme === 'function' && (q.theme || '') !== plan.theme){
    q.opacity = plan.themeOpacity;
    q.borders = plan.themeBorders;
    cqTheme(plan.theme);
  }
  activity('map views', `loaded the view ${v.name}`);
  toast(`${v.name}${plan.dropped.length
    ? ` · ${plan.dropped.length} layer(s) it names are not on this map` : ''}`);
  cvwPaint();
}

/* ---------- keeping them ---------- */

function cvwAdd(){
  const k = state.cvw, list = cvwList();
  if(!k) return;
  if(list.length >= CVW_MAX){
    k.err = `${CVW_MAX} saved views is the limit. Delete one to save another.`;
    return cvwPaint();
  }
  const name = prompt('Save this view as:\n\n'
    + 'Which layers are drawn, in what order, at what opacity, the colours '
    + 'punched out of each, the terrain textures and the rivers and heights '
    + 'readings, the settlement '
    + 'names, and the colouring over the top. Not the zoom or the selection - '
    + 'those are about a place.',
    `${CVW_NAME} ${list.length + 1}`);
  if(name === null) return;
  const clean = String(name).trim();
  if(!clean) return;
  const at = list.findIndex(v => v.name.toLowerCase() === clean.toLowerCase());
  if(at >= 0 && !confirm(`Replace the saved view "${list[at].name}"?`)) return;
  const snap = cvwSnapshot(clean);
  if(at >= 0) list[at] = snap; else list.push(snap);
  k.err = '';
  activity('map views', `saved the view ${clean}`);
  cvwStore();
  cvwPaint();
}

//: Overwrite one with what is on screen now, without being asked for a name
//: again. The button people reach for after nudging one slider.
function cvwUpdate(i){
  const list = cvwList(), v = list[i];
  if(!v) return;
  if(!confirm(`Overwrite "${v.name}" with the view on screen now?`)) return;
  list[i] = cvwSnapshot(v.name);
  activity('map views', `updated the view ${v.name}`);
  cvwStore();
  cvwPaint();
}

function cvwRename(i){
  const list = cvwList(), v = list[i];
  if(!v) return;
  const name = prompt('Call this view:', v.name);
  if(name === null) return;
  const clean = String(name).trim();
  if(!clean || clean === v.name) return;
  v.name = clean;
  cvwStore();
  cvwPaint();
}

function cvwDelete(i){
  const list = cvwList(), v = list[i];
  if(!v) return;
  if(!confirm(`Delete the saved view "${v.name}"?\n\n`
    + 'It is a set of switches, not a file - nothing about the mod changes.')) return;
  list.splice(i, 1);
  activity('map views', `deleted the view ${v.name}`);
  cvwStore();
  cvwPaint();
}

/* ---------- drawing ---------- */

function cvwPaint(){
  const el = document.getElementById('cmViews');
  if(!el) return;
  el.innerHTML = cvwHtml();
}

//: One line saying what a preset is, without opening it: how many layers it
//: draws, and whether it carries a colouring.
function cvwSummary(v){
  const on = Object.keys((v && v.on) || {}).filter(code => v.on[code]);
  const bits = [`${on.length} layer${on.length === 1 ? '' : 's'}`];
  if(v.river && v.river.on) bits.push('rivers only');
  if(v.height_alpha) bits.push('heights as transparency');
  if(v.theme) bits.push(`coloured by ${v.theme.replace(/_/g, ' ')}`);
  const hidden = Object.values((v && v.hide) || {})
    .reduce((n, a) => n + (Array.isArray(a) ? a.length : 0), 0);
  if(hidden) bits.push(`${hidden} colour${hidden === 1 ? '' : 's'} punched out`);
  return bits.join(' · ');
}

function cvwHtml(){
  const k = state.cvw;
  if(!k) return '';
  const list = cvwList();
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cvwToggle()"
      title="Save what the map looks like now under a name, and come back to it.
Which layers, in what order, at what opacity, with which colours punched out - and the colouring over the top."
      >\u{1F4D0} Views${k.open ? ' ✓' : ''}</button>
    ${list.length ? `<span class="count">${list.length} saved</span>` : ''}
  </div>`;
  if(!k.open) return head;
  return head + `<div class="cvwpanel">
    ${k.err ? `<div class="w-warn">${esc(k.err)}</div>` : ''}
    ${list.length ? list.map((v, i) => `<div class="cvwrow">
      <button class="cvwgo" onclick="cvwLoad(${i})"
        title="Draw the map this way">${esc(v.name)}</button>
      <span class="cvwbtn">
        <button onclick="cvwUpdate(${i})" title="Overwrite it with the view on screen now"
          >Update</button>
        <button onclick="cvwRename(${i})" title="Rename it">✎</button>
        <button onclick="cvwDelete(${i})" title="Delete it">✕</button></span>
      <div class="count">${esc(cvwSummary(v))}</div>
    </div>`).join('') : `<div class="count">No saved views yet. Set the layers
      up the way you want to read this map, then save it - the same set of
      switches comes back on any mod, because the ten layer codes are the
      engine's own and mean the same thing in all of them.</div>`}
    <button onclick="cvwAdd()" class="primary">Save this view…</button>
  </div>`;
}
