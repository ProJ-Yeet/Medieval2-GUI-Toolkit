/* mapquery.js - Campaign Map: the query panel, the themes and the information maps

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE QUERY PANEL - Phase 16g.

   Every name here starts `cq`, and none of them existed anywhere else in the
   tree before this phase - checked, the way 16e checked `cp` and 16f checked
   `cchk`.

   THE PANEL DECIDES NOTHING, AGAIN. Python owns every filter, works out which
   provinces match, builds the sentence that says why each one does, and hands
   back a table of region colour to paint colour. This file draws the controls,
   posts what is picked in them, and recolours. There is no copy of "has a
   port" on this side, which is the same ruling the brush makes about pixels
   and the validator makes about rules.

   A COLOURING IS A RECOLOUR OF A LAYER THAT IS ALREADY HERE. The regions layer
   is one pixel per tile and the browser is already holding it, so a theme is
   one pass over at most a megapixel through a lookup table - the same
   operation 16d's `cmapMask` does when it punches a colour out of a layer.
   Nothing is fetched to change theme, and nothing on the interaction path
   touches it: it is built when the theme changes and copied after that.

   THE BORDER IS DRAWN FROM THE GROUP, NOT FROM THE COLOUR. Two provinces of
   one faction share a colour and must not have a line between them; two
   provinces of two factions that happen to be given the same colour would. So
   the pass compares the group each region is in, which is what the server's
   own border pass compares, and the picture on screen and the exported TGA
   agree about where a frontier is.
   ===================================================================== */

//: How many matched provinces the list shows before it stops and counts the
//: rest. The server folds at 400; this is what one panel can usefully scroll.
const CQ_ROWS = 80;

//: How far in the map zooms when it goes to a province. Enough to count tiles,
//: which is the whole reason for going.
const CQ_ZOOM = 6;

/* ---------- state ---------- */

/* Kept beside `state.cmap` rather than inside it, like the paint tool and the
   validator: `loadCampmap` rebuilds that object whenever the mod changes, and
   which question somebody is asking is a habit rather than a fact about the
   map. `voc` is the server's own vocabulary and is never edited here. */
function cqNew(mod){
  return {mod, open: false, tab: 'query', busy: false, err: '',
          voc: null, rules: [], match: 'all', res: null,
          theme: '', col: null, opacity: 0.85, borders: true,
          exporting: false, exported: null};
}

function cqOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cq || state.cq.mod !== c.mod){
    state.cq = cqNew(c.mod);
    if(c) { c.overlay = null; c.overlayKey = ''; }
  }
  cqPaint();
}

function cqToggle(){
  const k = state.cq;
  if(!k) return;
  k.open = !k.open;
  activity('map query', k.open ? 'opened the query panel' : 'closed the query panel');
  if(k.open && !k.voc) cqLoadVocab();
  else cqPaint();
}

function cqTab(name){
  const k = state.cq;
  k.tab = name;
  cqPaint();
}

/* ---------- the wire ---------- */

async function cqLoadVocab(){
  const k = state.cq;
  if(!k || k.busy) return;
  k.busy = true; k.err = '';
  cqPaint();
  try{
    k.voc = await api.get(`/api/map/query/vocab?mod=${enc(k.mod)}`,
                          {label: 'reading what this map can be asked'});
  }catch(e){ k.err = errText(e); }
  finally{ k.busy = false; }
  if(state.cq === k) cqPaint();
}

async function cqRun(){
  const k = state.cq;
  if(!k || k.busy) return;
  k.busy = true; k.err = '';
  cqPaint();
  try{
    k.res = await api.post('/api/map/query',
                           {mod: k.mod, rules: k.rules, match: k.match});
    if(k.res.error) { k.err = k.res.error; k.res = null; }
  }catch(e){ k.err = errText(e); k.res = null; }
  finally{ k.busy = false; }
  if(state.cq !== k) return;
  if(k.res){
    activity('map query', `${k.rules.length} filter(s) -> ${k.res.count} province(s)`);
    // A query answer replaces a theme on the map: they are two different
    // colourings of one layer and showing both at once would be a picture
    // neither of them means.
    k.theme = ''; k.col = null;
    cqApply(k.res.colours, false);
  }
  cqPaint();
}

async function cqTheme(code){
  const k = state.cq;
  if(!code){
    k.theme = ''; k.col = null; k.res = null;
    cqApply(null);
    cqPaint();
    return;
  }
  k.busy = true; k.err = '';
  cqPaint();
  try{
    k.col = await api.get(`/api/map/colouring?mod=${enc(k.mod)}&code=${enc(code)}`,
                          {label: 'building that map'});
    k.theme = code;
    k.res = null;
    activity('map query', `showed the ${k.col.label} map`);
    cqApply(k.col.colours, k.borders && k.col.borders);
  }catch(e){ k.err = errText(e); k.theme = ''; k.col = null; }
  finally{ k.busy = false; }
  if(state.cq === k) cqPaint();
}

async function cqExport(what){
  const k = state.cq;
  if(!k || k.exporting) return;
  k.exporting = true; k.err = ''; k.exported = null;
  cqPaint();
  const body = {mod: k.mod, what, reveal: true};
  if(what === 'colouring') body.code = k.theme;
  if(what === 'query'){ body.rules = k.rules; body.match = k.match; }
  let r;
  try{ r = await api.post('/api/map/export', body); }
  catch(e){ r = {error: errText(e)}; }
  finally{ k.exporting = false; }
  if(state.cq !== k) return;
  k.err = r.error || '';
  if(!r.error){
    k.exported = r;
    activity('map export', `${r.count} TGA(s), ${Math.round(r.bytes / 1024)} KB`);
    toast(`${r.count} file${r.count === 1 ? '' : 's'} written to ${r.folder}`, 7000);
  }
  cqPaint();
}

/* ---------- the rules ---------- */

function cqFilter(code){
  const k = state.cq;
  return ((k.voc && k.voc.filters) || []).find(f => f.code === code) || null;
}

function cqAdd(code){
  const k = state.cq, f = cqFilter(code);
  if(!f || f.off) return;
  const rule = {code, value: '', negate: false};
  // A picker with one thing in it is a picker nobody wants to open, and a
  // rule with nothing picked cannot run - so the commonest value goes in.
  if(f.values.length) rule.value = f.values[0].value;
  if(f.kind === 'share') rule.min = 50;
  k.rules.push(rule);
  cqPaint();
}

function cqDrop(i){
  state.cq.rules.splice(i, 1);
  if(!state.cq.rules.length){ state.cq.res = null; cqApply(null); }
  cqPaint();
}

function cqSet(i, slot, value){
  const r = state.cq.rules[i];
  if(!r) return;
  r[slot] = value;
  cqPaint();
}

function cqMatch(mode){
  state.cq.match = mode;
  cqPaint();
}

/* ---------- painting the map ---------- */

/* Recolour the regions layer through a table, and hand it to the renderer.

   `table` is {packed region colour: [r,g,b]} exactly as the server built it,
   or null to take the colouring off. The result goes in `c.overlay`, which
   `cmapCompose` draws last - so the layer stack underneath is untouched and
   ticking layers on and off still works while a theme is on.

   One pass over the layer, on the change that causes it, cached by the table
   it was built from. Rule 4 of 16c holds: nothing here is on the interaction
   path. */
function cqApply(table, borders){
  const c = state.cmap;
  if(!c) return;
  if(!table){
    c.overlay = null; c.overlayKey = ''; c.compKey = '';
    cmapCompose(); cmapPaint();
    return;
  }
  const L = c.layers.regions;
  if(!L || !(L.cv || L.img)){
    // The regions layer has not arrived yet. Ask for it and come back: a theme
    // is a recolour of that picture and there is nothing to recolour without it.
    cmapFetchLayer(c, 'regions').then(() => {
      if(state.cmap === c) cqApply(table, borders);
    });
    return;
  }
  const wantKey = JSON.stringify([Object.keys(table).length, borders,
                                  state.cq && state.cq.theme,
                                  state.cq && state.cq.res && state.cq.res.count]);
  if(c.overlayKey === wantKey && c.overlay) { cmapCompose(); cmapPaint(); return; }

  const src = L.cv || L.img;
  const w = src.naturalWidth || src.width, h = src.naturalHeight || src.height;
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const x = cv.getContext('2d', {willReadFrequently: true});
  x.imageSmoothingEnabled = false;
  x.drawImage(src, 0, 0);
  const im = x.getImageData(0, 0, w, h), d = im.data;
  // group id per pixel, so a border can be drawn between two groups rather
  // than between two colours - see the header
  const group = borders ? new Int32Array(w * h).fill(-1) : null;
  const seen = new Map();
  for(let i = 0, n = w * h; i < n; i++){
    const p = i * 4;
    const rgb = (d[p] << 16) | (d[p + 1] << 8) | d[p + 2];
    const to = table[rgb];
    if(!to){ d[p + 3] = 0; continue; }
    d[p] = to[0]; d[p + 1] = to[1]; d[p + 2] = to[2]; d[p + 3] = 255;
    if(group){
      let g = seen.get(rgb);
      if(g === undefined){ g = seen.size; seen.set(rgb, g); }
      group[i] = g;
    }
  }
  if(group) cqBorders(d, group, w, h);
  x.putImageData(im, 0, 0);
  c.overlay = cv; c.overlayKey = wantKey; c.compKey = '';
  cmapCompose(); cmapPaint();
}

/* The line where two groups meet.

   Four-connected, drawn on the left-hand and upper tile of each pair, which is
   the direction campmap's own adjacency pass compares in and the direction the
   server's export draws in. A tile in no group takes no line: an uncoloured
   province is not a frontier, it is a province the mod says nothing about. */
function cqBorders(d, group, w, h){
  const edge = [];
  for(let y = 0; y < h; y++){
    const row = y * w;
    for(let x = 0; x < w; x++){
      const g = group[row + x];
      if(g < 0) continue;
      const right = x + 1 < w ? group[row + x + 1] : g;
      const down = y + 1 < h ? group[row + w + x] : g;
      if((right >= 0 && right !== g) || (down >= 0 && down !== g)) edge.push(row + x);
    }
  }
  const b = (state.cq && state.cq.voc && state.cq.voc.border) || [18, 18, 22];
  for(const i of edge){
    const p = i * 4;
    d[p] = b[0]; d[p + 1] = b[1]; d[p + 2] = b[2]; d[p + 3] = 255;
  }
}

function cqOpacity(v){
  const k = state.cq;
  k.opacity = v / 100;
  const c = state.cmap;
  if(c){ c.overlayAlpha = k.opacity; c.compKey = ''; cmapCompose(); cmapPaint(); }
  cqPaint();
}

function cqBordersToggle(on){
  const k = state.cq;
  k.borders = on;
  if(k.col) cqApply(k.col.colours, on && k.col.borders);
  cqPaint();
}

/* Centre the map on a province and pick it.

   Same as the validator's jump and for the same reason: a province nobody can
   find is an answer nobody can use. The tile is the region's anchor, which
   campmap already worked out is a pixel genuinely inside it rather than a
   centroid that can land in the sea. */
function cqGo(r){
  const c = state.cmap;
  if(!c || !r.tile) return;
  const [w, h] = cmapCanvasSize();
  const v = c.view;
  v.zoom = Math.max(v.zoom, CQ_ZOOM);
  v.ox = w / 2 - (r.tile[0] + 0.5) * v.zoom;
  v.oy = h / 2 - (r.tile[1] + 0.5) * v.zoom;
  v.fitted = true;
  cmapPick(r.tile);
  activity('map query', `went to ${r.name}`);
}

/* ---------- drawing ---------- */

function cqPaint(){
  const el = document.getElementById('cmQuery');
  if(!el) return;
  el.innerHTML = cqHtml();
  cqWire();
}

function cqWire(){
  const box = document.getElementById('cmQuery');
  if(!box) return;
  box.querySelectorAll('[data-cqval]').forEach(sel => sel.onchange = () =>
    cqSet(+sel.dataset.cqval, 'value', sel.value));
  box.querySelectorAll('[data-cqnum]').forEach(inp => inp.onchange = () =>
    cqSet(+inp.dataset.cqnum, inp.dataset.slot, inp.value === '' ? '' : +inp.value));
  box.querySelectorAll('[data-cqtext]').forEach(inp => inp.oninput = () =>
    cqSet(+inp.dataset.cqtext, 'value', inp.value));
  box.querySelectorAll('[data-cqneg]').forEach(cb => cb.onchange = () =>
    cqSet(+cb.dataset.cqneg, 'negate', cb.checked));
  const add = box.querySelector('[data-cqadd]');
  if(add) add.onchange = () => { const v = add.value; add.value = ''; cqAdd(v); };
  const th = box.querySelector('[data-cqtheme]');
  if(th) th.onchange = () => cqTheme(th.value);
}

function cqHtml(){
  const k = state.cq;
  if(!k) return '';
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cqToggle()"
      title="Ask this map which provinces are which, and colour it by what it says."
      >\u{1F5FA} Query${k.open ? ' ✓' : ''}</button>
    ${k.res ? `<span class="count">${k.res.count} of ${k.res.of} provinces</span>` : ''}
    ${k.theme && k.col ? `<span class="count">${esc(k.col.label)}</span>` : ''}
    ${k.busy ? `<span class="count">working…</span>` : ''}
  </div>`;
  if(!k.open) return head;
  if(k.err && !k.voc) return head + `<div class="cqpanel w-bad">${esc(k.err)}</div>`;
  if(!k.voc) return head + `<div class="cqpanel count">reading what this map
    can be asked…</div>`;
  return head + `<div class="cqpanel">
    <div class="cqtabs">
      <button class="${k.tab === 'query' ? 'on' : ''}" onclick="cqTab('query')"
        >Filters</button>
      <button class="${k.tab === 'maps' ? 'on' : ''}" onclick="cqTab('maps')"
        >Themes and information maps</button>
      <button class="${k.tab === 'export' ? 'on' : ''}" onclick="cqTab('export')"
        >Export</button>
    </div>
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    ${k.tab === 'query' ? cqFiltersHtml()
      : k.tab === 'maps' ? cqMapsHtml() : cqExportHtml()}
    ${cqSkippedHtml()}
  </div>`;
}

//: What could not be read at all, said once at the bottom rather than repeated
//: on every filter that needed it.
function cqSkippedHtml(){
  const k = state.cq;
  const s = (k.voc && k.voc.skipped) || [];
  if(!s.length) return '';
  return `<div class="cqskip"><div class="k">Not read</div>
    ${s.map(x => `<div class="count"><b>${esc(x.what)}</b> ${esc(x.why)}</div>`).join('')}
  </div>`;
}

function cqFiltersHtml(){
  const k = state.cq;
  const groups = [];
  for(const f of k.voc.filters){
    let g = groups.find(x => x.name === f.group);
    if(!g) groups.push(g = {name: f.group, items: []});
    g.items.push(f);
  }
  const picker = `<select data-cqadd>
    <option value="">Add a filter…</option>
    ${groups.map(g => `<optgroup label="${esc(g.name)}">${g.items.map(f =>
      `<option value="${esc(f.code)}" ${f.off ? 'disabled' : ''}>${esc(f.label)}${
        f.off ? ' - off' : (f.values.length ? ` (${f.values.length})` : '')
      }</option>`).join('')}</optgroup>`).join('')}
  </select>`;

  const off = k.voc.filters.filter(f => f.off);
  return `<div class="cqrules">
    <div class="cqhead">
      ${picker}
      <span class="cqmatch">
        <label class="chk"><input type="radio" name="cqmatch" ${k.match === 'all' ? 'checked' : ''}
          onchange="cqMatch('all')"> all of them</label>
        <label class="chk"><input type="radio" name="cqmatch" ${k.match === 'any' ? 'checked' : ''}
          onchange="cqMatch('any')"> any of them</label>
      </span>
      <button class="primary" onclick="cqRun()" ${k.rules.length ? '' : 'disabled'}
        >Find provinces</button>
    </div>
    ${k.rules.length ? k.rules.map(cqRuleHtml).join('')
      : `<div class="count">No filter yet. Every one of them is a question the
         mod's own files answer - who starts holding a province, what is buried
         under it, which mercenaries it sells, whose win conditions name it.</div>`}
    ${off.length ? `<div class="cqoff"><div class="k">Off on this mod</div>
      ${off.map(f => `<div class="count"><b>${esc(f.label)}</b> ${esc(f.off)}</div>`).join('')}
    </div>` : ''}
    ${cqResultHtml()}
  </div>`;
}

function cqRuleHtml(r, i){
  const f = cqFilter(r.code);
  if(!f) return '';
  let body = '';
  if(f.kind === 'choice' || f.kind === 'share'){
    body = `<select data-cqval="${i}">${f.values.map(v =>
      `<option value="${esc(v.value)}" ${v.value === r.value ? 'selected' : ''}
        >${esc(v.label)} · ${v.count}</option>`).join('')}</select>`;
    if(f.kind === 'share') body += ` at least <input type="number" min="0" max="100"
      value="${r.min == null ? 50 : r.min}" data-cqnum="${i}" data-slot="min"
      style="width:5em">${esc(f.unit || '')}`;
  }else if(f.kind === 'range'){
    body = `from <input type="number" value="${r.min == null ? '' : r.min}"
        data-cqnum="${i}" data-slot="min" style="width:6em" placeholder="any">
      to <input type="number" value="${r.max == null ? '' : r.max}"
        data-cqnum="${i}" data-slot="max" style="width:6em" placeholder="any">
      ${esc(f.unit || '')}`;
  }else if(f.kind === 'text'){
    body = `<input type="text" value="${esc(r.value || '')}" data-cqtext="${i}"
      placeholder="part of a name" style="width:14em">`;
  }else{
    body = `<span class="count">on</span>`;
  }
  return `<div class="cqrule">
    <b>${esc(f.label)}</b> ${body}
    <label class="chk" title="Keep the provinces this does NOT describe">
      <input type="checkbox" data-cqneg="${i}" ${r.negate ? 'checked' : ''}> not</label>
    <button onclick="cqDrop(${i})" title="Remove this filter">✕</button>
    ${f.note ? `<div class="count">${esc(f.note)}</div>` : ''}
    <div class="count cqsrc">${esc(f.source)}</div>
  </div>`;
}

function cqResultHtml(){
  const k = state.cq, res = k.res;
  if(!res) return '';
  const rows = res.regions.slice(0, CQ_ROWS);
  return `<div class="cqres">
    <div class="k">${res.count} province${res.count === 1 ? '' : 's'}
      <span class="count">of ${res.of} · ${res.tiles.toLocaleString()} tiles ·
        ${res.ms} ms</span></div>
    ${res.off.length ? res.off.map(o => `<div class="w-warn">
      <b>${esc(o.label || o.code)}</b> was not asked: ${esc(o.why)}</div>`).join('') : ''}
    ${res.count ? rows.map(r => `<div class="cqrow" onclick='cqGo(${
        JSON.stringify({name: r.name, tile: r.tile}).replace(/'/g, "&#39;")})'>
        <b>${esc(r.shown || r.name)}</b>
        <span class="count">${esc(r.name)}${r.owner ? ' · ' + esc(r.owner) : ''}
          · ${r.pixels.toLocaleString()} tiles</span>
        <div class="count">${r.why.map(esc).join(' · ')}</div>
      </div>`).join('')
      : `<div class="count">Nothing on this map answers all of that. The filters
         that did run are listed above with what each one is reading.</div>`}
    ${res.regions.length > CQ_ROWS ? `<div class="count">and ${
      res.count - CQ_ROWS} more, all of them coloured on the map</div>` : ''}
    ${res.count ? `<button onclick="cqExport('query')" ${k.exporting ? 'disabled' : ''}
      >Export this as a TGA</button>` : ''}
  </div>`;
}

function cqMapsHtml(){
  const k = state.cq;
  const groups = [];
  for(const c of k.voc.colourings){
    let g = groups.find(x => x.name === c.group);
    if(!g) groups.push(g = {name: c.group, items: []});
    g.items.push(c);
  }
  const col = k.col;
  return `<div class="cqmaps">
    <div class="cqhead">
      <select data-cqtheme>
        <option value="">No colouring - the layers as they are</option>
        ${groups.map(g => `<optgroup label="${esc(g.name)}">${g.items.map(c =>
          `<option value="${esc(c.code)}" ${c.code === k.theme ? 'selected' : ''}
            ${c.off ? 'disabled' : ''}>${esc(c.label)}${c.off ? ' - off' : ''}</option>`
          ).join('')}</optgroup>`).join('')}
      </select>
      <label class="chk"><input type="checkbox" ${k.borders ? 'checked' : ''}
        onchange="cqBordersToggle(this.checked)"> political borders</label>
      <input type="range" min="20" max="100" value="${Math.round(k.opacity * 100)}"
        oninput="cqOpacity(+this.value)" title="How much of the layers below shows through">
      <span class="cmpct">${Math.round(k.opacity * 100)}%</span>
    </div>
    ${col ? cqLegendHtml(col) : `<div class="count">Pick a theme to colour every
      province by who holds it, or an information map to colour it by what is in
      it. Both are the region layer recoloured through a table Python builds, so
      what is on screen and what an export writes are the same picture.</div>`}
  </div>`;
}

function cqLegendHtml(col){
  const k = state.cq;
  return `<div class="cqleg">
    <div class="k">${esc(col.label)}
      <span class="count">${col.groups.length} group${col.groups.length === 1 ? '' : 's'}${
        col.ungrouped ? ` · ${col.ungrouped} province(s) in none` : ''}</span></div>
    ${col.note ? `<div class="count">${esc(col.note)}</div>` : ''}
    ${(col.substituted || []).length ? `<div class="w-warn">
      ${col.substituted.length} faction${col.substituted.length === 1 ? '' : 's'}
      declare a colour too close to something already on the map to tell apart and
      ${col.substituted.length === 1 ? 'is' : 'are'} drawn in the fallback palette:
      ${col.substituted.map(s => `${esc(s.value)} (rgb(${s.declared.join(', ')}),
        the same as ${esc(s.clash)})`).join('; ')}</div>` : ''}
    <div class="cqswatches">
      ${col.groups.map(g => `<div class="cqsw" title="${esc(g.names.join(', '))}">
        <i style="background:rgb(${g.rgb.join(',')})"></i>
        <b>${esc(g.label)}</b>
        <span class="count">${g.regions} · ${g.pixels.toLocaleString()} tiles</span>
      </div>`).join('')}
    </div>
    <div class="count cqsrc">${esc(col.source)}</div>
    <button onclick="cqExport('colouring')" ${k.exporting ? 'disabled' : ''}
      >Export this as a TGA</button>
  </div>`;
}

function cqExportHtml(){
  const k = state.cq;
  const done = k.exported;
  return `<div class="cqexport">
    <div class="count">Every export is written into the toolkit's cache and
      never into the mod: it is a picture of somebody else's files, and a tool
      that drops forty TGAs into <code>data/world/maps/base</code> has changed a
      mod nobody asked it to change. Each one is written in the shape of this
      mod's own <code>map_regions.tga</code>, so it opens in whatever made the
      map.</div>
    <div class="cqhead">
      <button class="primary" onclick="cqExport('factions')"
        ${k.exporting ? 'disabled' : ''}>Every faction, one TGA each</button>
      <button onclick="cqExport('colouring')"
        ${k.exporting || !k.theme ? 'disabled' : ''}>The colouring on screen</button>
      <button onclick="cqExport('query')"
        ${k.exporting || !(k.res && k.res.count) ? 'disabled' : ''}>The query result</button>
    </div>
    ${k.exporting ? `<div class="count">writing…</div>` : ''}
    ${done ? `<div class="cqres"><div class="k">${done.count} file${
      done.count === 1 ? '' : 's'} <span class="count">${
      Math.round(done.bytes / 1024).toLocaleString()} KB · ${done.ms} ms</span></div>
      <div class="count">${esc(done.folder)}</div>
      ${done.files.slice(0, 40).map(f => `<div class="count">${esc(f.name)}
        - ${esc(f.label)}, ${f.regions} province(s)</div>`).join('')}
      ${done.files.length > 40 ? `<div class="count">and ${
        done.files.length - 40} more</div>` : ''}
    </div>` : ''}
    ${(done && done.skipped || []).map(s => `<div class="w-warn">
      <b>${esc(s.what)}</b> ${esc(s.why)}</div>`).join('')}
  </div>`;
}
