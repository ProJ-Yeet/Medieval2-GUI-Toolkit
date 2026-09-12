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
          // 23b, T12. `fill` is how the colouring meets the map: `solid` lays
          // it over, `tint` colours what is there and keeps its light, which is
          // the one to use over 23a's textures. `borderPos` and `borderEvery`
          // are his other two: where the line goes, and whether it is drawn
          // between blocs or round every province.
          fill: 'solid', borderPos: 'edge', borderEvery: false,
          exporting: false, exported: null};
}

function cqOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cq || state.cq.mod !== c.mod){
    state.cq = cqNew(c.mod);
    if(c){ c.overlay = null; c.overlayEdge = null; c.overlayKey = ''; }
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
    k.voc = await api.get(`/api/map/query/vocab?mod=${enc(k.mod)}${cmapCampQ()}`,
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
    cqApply(k.res, k.borders);
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
    k.col = await api.get(`/api/map/colouring?mod=${enc(k.mod)}&code=${enc(code)}`
                          + cmapCampQ(),
                          {label: 'building that map'});
    k.theme = code;
    k.res = null;
    activity('map query', `showed the ${k.col.label} map`);
    cqApply(k.col, k.borders);
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
  if(what === 'colouring'){
    body.code = k.theme;
    // 23b: the frontiers on the screen are the frontiers in the file. The tint
    // is deliberately not sent - it is how the colouring is laid over the map,
    // like the opacity slider beside it, and this writes the colouring.
    body.borders = k.borders;
    body.border_position = k.borderPos;
    body.border_every = k.borderEvery;
  }
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
   or null to take the colouring off. `borders` says whether frontiers are worth
   drawing for this colouring at all; how they are drawn is `state.cq`'s, and so
   is whether the fill is laid over the map or tinted into it.

   TWO canvases out, not one (23b, T12). `c.overlay` is the fill and `c.overlayEdge`
   the frontiers, because in tint mode they are drawn differently: the fill takes
   the colour of the theme and the light of the map, and a line has to stay a
   line. `cmapThemeDraw` is where that happens; this only decides which pixels.

   One pass over the layer, on the change that causes it, cached by everything
   the pass reads. Rule 4 of 16c holds: nothing here is on the interaction path. */
function cqApply(col, borders){
  const c = state.cmap, k = state.cq;
  if(!c) return;
  const table = col && col.colours, bands = col && col.bands;
  // the one place the screen is told how to draw what this builds, so a theme
  // applied from a saved view cannot arrive with last view's fill still set
  c.overlayFill = (k && k.fill) || 'solid';
  c.overlayAlpha = k ? k.opacity : 0.85;
  if(!table){
    c.overlay = null; c.overlayEdge = null; c.overlayKey = '';
    cmapCompose(); cmapPaint();
    return;
  }
  const L = c.layers.regions;
  if(!L || !(L.cv || L.img)){
    // The regions layer has not arrived yet. Ask for it and come back: a theme
    // is a recolour of that picture and there is nothing to recolour without it.
    cmapFetchLayer(c, 'regions').then(() => {
      if(state.cmap === c) cqApply(col, borders);
    });
    return;
  }
  const pos = (k && k.borderPos) || 'edge';
  const every = !!(k && k.borderEvery);
  const wantKey = JSON.stringify([Object.keys(table).length, borders, pos, every,
                                  k && k.theme, k && k.res && k.res.count]);
  if(c.overlayKey === wantKey && c.overlay){ cmapCompose(); cmapPaint(); return; }

  // the layer's bytes, copied - never the picture read back, which a browser
  // may alter (see cmapFetchLayer), and a theme is an exact-colour lookup
  const R = cmapRawOf(L);
  const w = R.w, h = R.h;
  c.overlay = cqCanvas(cqFill(R.data, w, h, table), w, h);
  c.overlayEdge = (borders && bands)
    ? cqCanvas(cqBorders(cqGroups(R.data, w, h, bands, every), w, h, pos), w, h)
    : null;
  c.overlayKey = wantKey;
  cmapCompose(); cmapPaint();
}

/* The region layer recoloured through the table: the fill, and only the fill.

   A province in no group comes out transparent rather than in some "none"
   colour, so what is under it is what shows - which is the whole of how a
   colouring and the layer stack get along. */
function cqFill(raw, w, h, table){
  const im = cmapImageData(new Uint8ClampedArray(raw), w, h), d = im.data;
  for(let i = 0, n = w * h; i < n; i++){
    const p = i * 4;
    const to = table[(d[p] << 16) | (d[p + 1] << 8) | d[p + 2]];
    if(!to){ d[p + 3] = 0; continue; }
    d[p] = to[0]; d[p + 1] = to[1]; d[p + 2] = to[2]; d[p + 3] = 255;
  }
  return im;
}

/* A group id per tile, which is what a border is worked out from. Pure.

   `bands` is the server's, straight out of `Colouring.payload`: which group
   each province is in, -1 for one the colouring has nothing to say about, and
   absent for anything that is not a province. It is NOT `colours`, and that is
   the point - a presence map has a real group labelled "none" painted the same
   grey a province in no group is painted, so the colour cannot tell the two
   apart. Reading the group off the colour drew a frontier round every
   ungrouped province here and none in the exported file.

   `every` is T12's "all regions": each province its own group, so every
   boundary is a frontier, an uncoloured province included - it has a boundary
   whether or not the theme has anything to say about it.

   Three states out, and the third is the one worth writing down. -1 is "not a
   province", and a neighbour that is -1 never makes a frontier: that is what
   keeps the coastline out of it. -2 is a province in no group, and it is not
   the same thing - it draws no line of its own, and a coloured province beside
   it does, because the edge of what a theme covers is a real edge.
   `unittransfer.mapquery._label_colours` uses the same two negatives for the
   same two reasons, and the suite runs both passes over one map to check they
   mark the same tiles. */
function cqGroups(raw, w, h, bands, every){
  const group = new Int32Array(w * h).fill(-1);
  for(let i = 0, n = w * h; i < n; i++){
    const p = i * 4;
    const rgb = (raw[p] << 16) | (raw[p + 1] << 8) | raw[p + 2];
    const band = bands[rgb];
    if(band === undefined) continue;             // not a province
    group[i] = every ? rgb : (band < 0 ? -2 : band);
  }
  return group;
}

//: A canvas holding these pixels, written and never read - campmap's rule.
function cqCanvas(im, w, h){
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const x = cv.getContext('2d');
  x.imageSmoothingEnabled = false;
  x.putImageData(im, 0, 0);
  return cv;
}

/* The line where two groups meet, as its own transparent picture.

   Four-connected. `edge` marks the left-hand and upper tile of each pair, which
   is the direction campmap's own adjacency pass compares in and the direction
   the server's export draws in: a hairline that sits on the frontier and
   belongs to neither side. `inside` marks both sides instead - TWMapReader's
   `borderPosInside`, which is the set of a region's own border tiles - and it
   is the one that still reads at a zoom where a hairline has vanished, or over
   a texture.

   A tile in no group takes no line, and neither does one whose only different
   neighbour is the sea or a marker: an uncoloured province is not a frontier,
   and a coastline is not one at all. */
function cqBorders(group, w, h, position){
  const im = cmapImageData(new Uint8ClampedArray(w * h * 4), w, h), d = im.data;
  const b = (state.cq && state.cq.voc && state.cq.voc.border) || [18, 18, 22];
  const inside = position === 'inside';
  //: a neighbour is a different side iff it is a province and not this group.
  //: -2, a province in no group, counts as different and is why this is not a
  //: plain `>= 0` test.
  const other = (n, g) => n !== -1 && n !== g;
  for(let y = 0; y < h; y++){
    const row = y * w;
    for(let x = 0; x < w; x++){
      const i = row + x, g = group[i];
      if(g < 0) continue;
      const right = x + 1 < w ? group[i + 1] : -1;
      const down = y + 1 < h ? group[i + w] : -1;
      let hit = other(right, g) || other(down, g);
      if(!hit && inside){
        const left = x ? group[i - 1] : -1;
        const up = y ? group[i - w] : -1;
        hit = other(left, g) || other(up, g);
      }
      if(!hit) continue;
      const p = i * 4;
      d[p] = b[0]; d[p + 1] = b[1]; d[p + 2] = b[2]; d[p + 3] = 255;
    }
  }
  return im;
}

/* The opacity slider. Since 23b it is a repaint and not a recompose: the
   colouring is drawn onto the screen rather than into the layer composite, so
   dragging this no longer rebuilds a megapixel canvas per pixel of travel. */
function cqOpacity(v){
  const k = state.cq;
  k.opacity = v / 100;
  const c = state.cmap;
  if(c){ c.overlayAlpha = k.opacity; cmapPaint(); }
  cqPaint();
}

//: Everything about how the colouring is drawn, in one setter: the three T12
//: controls and the borders tickbox all end in the same rebuild.
function cqDraw(field, value){
  const k = state.cq;
  if(!k) return;
  k[field] = value;
  const c = state.cmap;
  if(field === 'fill' && c) c.overlayFill = value;
  activity('map query', `${field} ${value}`);
  if(k.col) cqApply(k.col, k.borders);
  else if(k.res) cqApply(k.res, k.borders);
  cqPaint();
}

function cqBordersToggle(on){ cqDraw('borders', on); }

/* Centre the map on a province and pick it.

   Same as the validator's jump and for the same reason: a province nobody can
   find is an answer nobody can use. The tile is the region's anchor, which
   campmap already worked out is a pixel genuinely inside it rather than a
   centroid that can land in the sea.

   The arithmetic itself is `cmapGoTile`, since 20b: this was one of three
   copies of it and the find box would have been a fourth. */
function cqGo(r){
  if(!r || !r.tile) return;
  cmapGoTile(r.tile, CQ_ZOOM, r.name);
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
      <span class="cmseg" title="How the colouring meets the map.
Solid lays it over. Tint takes the colour of the theme and the light of what is already
drawn, so 23a's terrain textures still read underneath - which is TWMapReader's HSB fill,
and the reason it exists: a colouring that paints over a textured map hides the map."
        >${[['solid', 'Solid'], ['tint', 'Tint']].map(([v, t]) =>
          `<button class="${k.fill === v ? 'on' : ''}"
            onclick="cqDraw('fill', '${v}')">${t}</button>`).join('')}</span>
      <input type="range" min="20" max="100" value="${Math.round(k.opacity * 100)}"
        oninput="cqOpacity(+this.value)" title="How much of the layers below shows through">
      <span class="cmpct">${Math.round(k.opacity * 100)}%</span>
    </div>
    <div class="cqhead">
      <label class="chk" title="Frontiers, on any colouring. Until 23b this tickbox
did nothing on an information map, because each colouring carried its own yes-or-no and
only the three themes said yes - so 'borders' on a fertility map was a control that
appeared to be broken. It is the switch now, and it means what it says."
        ><input type="checkbox" ${k.borders ? 'checked' : ''}
        onchange="cqBordersToggle(this.checked)"> borders</label>
      <span class="cmseg" title="Where the line goes. On the edge it sits between the
two provinces and belongs to neither. Inside draws it on both sides instead, which is what
still reads once a hairline has disappeared into the zoom or into a texture."
        >${[['edge', 'On the edge'], ['inside', 'Inside']].map(([v, t]) =>
          `<button class="${k.borderPos === v ? 'on' : ''}" ${k.borders ? '' : 'disabled'}
            onclick="cqDraw('borderPos', '${v}')">${t}</button>`).join('')}</span>
      <span class="cmseg" title="Between which. Groups draws the frontiers of the
colouring - two provinces of one faction have no line between them. Every province draws
every boundary, coloured or not. A coastline is never a frontier either way."
        >${[[false, 'Groups'], [true, 'Every province']].map(([v, t]) =>
          `<button class="${k.borderEvery === v ? 'on' : ''}" ${k.borders ? '' : 'disabled'}
            onclick="cqDraw('borderEvery', ${v})">${t}</button>`).join('')}</span>
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
