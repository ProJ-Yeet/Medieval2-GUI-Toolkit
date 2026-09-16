/* stratview.js - the strat map's models, in 3D - 16k, moved by 49.

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE FILE BROWSER BEHIND THE STRAT-MAP 3D PANEL.

   `descr_model_strat.txt` declares the generals, agents and faction symbols,
   and the Strat map tab lists them - that is `stratmap.js`. But most of what
   the campaign map actually DRAWS is not in that file at all: a settlement's
   model is picked by level and culture out of `data/models_strat` with nothing
   naming the file, which is why Amon Hen and Minas Tirith are on the map and in
   no entry. So the panel has two ways in - a row's own 🧊, and this: every
   `.cas` the mod ships, grouped the way the folders group them, with a filter
   box because Third Age Reforged ships 250 of them.

   16k put this in the campaign map's side column. 49 moved it here, to the
   Models Editor, for the plain reason that it never edited anything on that
   screen and everything else about a mod's models is on this one. Nothing about
   the viewing changed: a click still hands the file to `v3MountCas`, and the
   decoding, the orbit and the framing are Phase 15's.

   Nothing is read off the disk until the panel is open, because a mod's model
   list is a directory walk.
   ===================================================================== */

function cmodNew(mod){
  return {mod, loading: false, err: '', models: null, filter: '', chosen: ''};
}

/* The list, fetched once per mod. Safe to call on every render, and that is
   why the early return does not repaint: `renderStratmap` runs on every
   keystroke in the entries search box, the panel is re-attached rather than
   rebuilt, and rewriting 926 rows under a list somebody is scrolling - to the
   same bytes - is the one cost this panel could have had. It paints when the
   box is empty, which is the render that just built it. */
async function cmodLoad(force){
  const mod = state.src;
  const was = state.cmod;
  if(was && was.mod === mod && was.models && !force){
    const el = document.getElementById('cmodBrowse');
    if(el && !el.innerHTML) cmodPaint();
    return;
  }
  if(was && was.mod === mod && was.loading && !force) return;
  const k = state.cmod = cmodNew(mod);
  k.filter = was && was.mod === mod ? was.filter : '';
  k.chosen = was && was.mod === mod ? was.chosen : '';
  k.loading = true;
  cmodPaint();
  let d;
  try{ d = await api.get(`/api/map/models?mod=${enc(mod)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cmod !== k) return;
  k.loading = false;
  if(d.error){ k.err = d.error; cmodPaint(); return; }
  k.models = d.models || [];
  cmodPaint();
}

/* Typed into rather than submitted, so the list narrows as you go. The value is
   kept on the panel and put back after the repaint - the input is inside the
   markup this redraws, so it would otherwise lose the caret on every letter. */
function cmodFilter(text){
  const k = state.cmod;
  if(!k) return;
  k.filter = text;
  cmodPaint();
  const el = document.getElementById('cmodFilter');
  if(el){ el.value = text; el.focus(); }
}

//: A click on a file draws it in the panel this list is inside. The entry the
//: panel was showing is let go, because a `.cas` is what it draws either way.
function cmodShow(rel){
  const k = state.cmod;
  if(!k) return;
  k.chosen = rel;
  if(typeof stmPrevShowFile === 'function') stmPrevShowFile(rel);
  else cmodPaint();
}

function cmodPaint(){
  const el = document.getElementById('cmodBrowse');
  if(!el) return;
  el.innerHTML = cmodHtml();
}

function cmodMatch(k){
  const want = (k.filter || '').trim().toLowerCase();
  const all = k.models || [];
  if(!want) return all;
  return all.filter(m => m.name.toLowerCase().includes(want)
                      || m.group.toLowerCase().includes(want));
}

function cmodHtml(){
  const k = state.cmod;
  if(!k) return '<div class="count">…</div>';
  if(k.loading) return '<div class="count">finding the models…</div>';
  if(k.err) return `<div class="w-warn">${esc(k.err)}</div>`;
  const models = k.models || [];
  if(!models.length)
    return `<div class="count">this mod ships no <code>data/models_strat</code>,
      so it uses the game's own strat models</div>`;

  const shown = cmodMatch(k);
  const groups = new Map();
  for(const m of shown){
    if(!groups.has(m.group)) groups.set(m.group, []);
    groups.get(m.group).push(m);
  }
  const rows = [...groups.entries()].map(([group, list]) => `
    <div class="k">${esc(group)} <span class="count">${list.length}</span></div>
    ${list.map(m => `<button class="cmodrow${k.chosen === m.rel ? ' on' : ''}"
        onclick="cmodShow('${q1(esc(m.rel))}')" title="${esc(m.rel)}"
        >${esc(m.name)}<span class="count">${Math.round(m.bytes/1024)} KB</span></button>`
      ).join('')}`).join('');
  return `<label class="v3f"><span>Find</span>
      <input id="cmodFilter" type="text" value="${esc(k.filter)}"
        placeholder="castle, general, symbol…"
        oninput="cmodFilter(this.value)"></label>
    <div class="count">${shown.length === models.length
      ? `${models.length} model file${models.length === 1 ? '' : 's'} under
         data/models_strat`
      : `${shown.length} of ${models.length}`}</div>
    <div class="cmodlist">${rows || '<div class="count">nothing by that name</div>'}</div>`;
}
