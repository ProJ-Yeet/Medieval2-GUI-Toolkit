/* mapfind.js - Campaign Map: one box, and the province it takes you to

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE FIND BOX - Phase 20b, T8.

   Every name here starts `cfd`, and none of them existed anywhere else in the
   tree before this phase - checked, the way 16g checked `cq` and 16f checked
   `cchk`. (`cmfind` in the stylesheet is the read's own findings list and is
   four hundred lines older than this; the classes here are `cfd` too.)

   A SEARCH BOX IS NOT A FILTER PANEL, and that is the whole reason this file
   exists next to `mapquery.js`. 16g can already answer "every province with a
   port, held by a faction of this culture, whose walls are stone" - twenty-four
   filters, a fact table joined on the server, a colouring over the result. What
   it cannot do is the thing you do twenty times an hour: you know the name, you
   want to be looking at it. That is one box, no dropdowns, and the answer under
   the cursor before you have finished typing.

   SO IT ASKS THE SERVER NOTHING. Every field it searches is already in the
   manifest the screen was handed when it opened: the province's code name, the
   settlement's code name, the region ID the engine numbers it with, and - since
   20b added them - what the player actually reads for both. A request per
   keystroke over 200 provinces would be a round trip to answer a question the
   page can answer in a fraction of a millisecond, and this screen's four
   performance rules all say the same thing about work on the interaction path.

   THREE TIERS AND NO FUZZINESS. Exact, then starts-with, then contains, each
   case-blind. Nothing here scores edit distance or transposes letters: a mod's
   province names are `Anorien_Province` and `Dol_Amroth_Province`, and a
   ranking nobody can predict is worse than a short list they can read. What a
   row does say is WHICH of the four names matched, because "Sauron" being a
   settlement in Third Age Reforged and `Sauron_Province` being the region round
   it is exactly the ambiguity somebody typing it is trying to resolve.
   ===================================================================== */

//: How many rows the list shows before it stops and counts the rest. Ten is
//: what fits without scrolling the side panel, and a search that returns more
//: than ten wants a narrower word rather than a longer list.
const CFD_ROWS = 10;

//: How far in the map zooms when it goes somewhere. The same number the query
//: panel uses, because arriving is arriving.
const CFD_ZOOM = 6;

/* The four names one province answers to, in the order a row prefers them.

   `key` is the field on a manifest region, `what` is what a row says it
   matched, and the order is the tie-break: with the same tier on two fields,
   the province's own name wins over its settlement's, and the words the player
   reads win over the code the files use. That last one is the house rule -
   localised name first, code name in brackets - applied to matching as well as
   to display. */
const CFD_FIELDS = [
  {key: 'shown', what: 'province'},
  {key: 'name', what: 'province code'},
  {key: 'shown_settlement', what: 'settlement'},
  {key: 'settlement_name', what: 'settlement code'},
];

/* ---------- state ----------

   Beside `state.cmap` like every other panel on this screen, and rebuilt when
   the mod changes. What is NOT kept is the text: a search is about the map in
   front of you, and a box that opens holding last week's word is a box you
   clear before you can use it. */
function cfdNew(mod){
  return {mod, open: false, q: '', hits: [], of: 0};
}

function cfdOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cfd || state.cfd.mod !== c.mod) state.cfd = cfdNew(c.mod);
  cfdPaint();
}

function cfdToggle(){
  const k = state.cfd;
  if(!k) return;
  k.open = !k.open;
  activity('map find', k.open ? 'opened the find box' : 'closed the find box');
  cfdPaint();
  if(k.open) cfdFocus();
}

//: The `f` key, and the button. Opening it and not putting the cursor in it
//: would be a box you have to click after asking for it.
function cfdFocus(){
  const el = document.getElementById('cfdBox');
  if(el){ el.focus(); el.select(); }
}

/* ---------- the search itself ----------

   Pure: a string and the manifest's region list in, ranked hits out. No DOM, no
   state, nothing fetched - which is what lets `tests/test_mapgo.py` run this
   very function in node over both installed mods' real region tables rather
   than over a Python copy of the ranking. */
function cfdSearch(text, regions){
  const q = String(text || '').trim().toLowerCase();
  if(!q) return [];
  // a bare number is a region ID, which is the one subject with no name at all
  // - the engine numbers provinces by first appearance in a row-major scan and
  // half the reference material talks about them that way
  const num = /^[0-9]+$/.test(q) ? parseInt(q, 10) : null;
  const out = [];
  for(const r of regions || []){
    if(!r || (!r.name && !r.settlement_name)) continue;   // an undeclared colour
    let best = null;
    if(num !== null && r.id === num)
      best = {tier: 0, field: -1, what: 'region ID', hit: String(r.id)};
    for(let i = 0; i < CFD_FIELDS.length; i++){
      const f = CFD_FIELDS[i], value = String(r[f.key] || '');
      if(!value) continue;
      const low = value.toLowerCase();
      const tier = low === q ? 0 : low.startsWith(q) ? 1
                 : low.includes(q) ? 2 : -1;
      if(tier < 0) continue;
      if(!best || tier < best.tier || (tier === best.tier && i < best.field))
        best = {tier, field: i, what: f.what, hit: value};
    }
    if(!best) continue;
    out.push({
      name: r.name, shown: r.shown || '', settlement: r.settlement_name || '',
      shown_settlement: r.shown_settlement || '',
      id: r.id, pixels: r.pixels || 0, declared: r.declared !== false,
      what: best.what, hit: best.hit, tier: best.tier,
      // a settlement match goes to the settlement's own pixel when the map has
      // one; everything else goes to the anchor, which campmap already worked
      // out is a tile genuinely inside the province
      tile: (best.field >= 2 && r.settlement) ? r.settlement : (r.anchor || null),
    });
  }
  out.sort((a, b) => a.tier - b.tier
    || (b.pixels - a.pixels)
    || String(a.shown || a.name).localeCompare(String(b.shown || b.name)));
  return out;
}

function cfdSet(text){
  const k = state.cfd, c = state.cmap;
  if(!k || !c) return;
  k.q = text;
  const hits = cfdSearch(text, c.man.regions);
  k.of = hits.length;
  k.hits = hits.slice(0, CFD_ROWS);
  cfdResults();
}

/* Centre the map on a hit and pick it.

   Through `cmapGoTile`, which is the one copy of that arithmetic - the query
   panel and the validator both jump the same way, and 20b made a third caller
   the point at which three copies became one. */
function cfdGo(i){
  const k = state.cfd, hit = k && k.hits[i];
  if(!hit || !hit.tile) return;
  cmapGoTile(hit.tile, CFD_ZOOM, hit.name);
  activity('map find', `went to ${hit.shown || hit.name} (${k.q})`);
}

//: Enter goes to the first hit, which is what a box with a list under it
//: promises. Escape gives the map its keys back.
function cfdKey(e){
  if(e.key === 'Enter'){ e.preventDefault(); cfdGo(0); }
  else if(e.key === 'Escape'){ e.preventDefault(); e.target.blur(); }
}

/* ---------- drawing ---------- */

function cfdPaint(){
  const el = document.getElementById('cmFind');
  if(!el) return;
  el.innerHTML = cfdHtml();
  cfdWire();
}

//: The list alone. Typing rebuilds one <div> rather than the box the cursor is
//: in, because rewriting an <input> under somebody's fingers loses the caret.
function cfdResults(){
  const el = document.getElementById('cfdRes');
  if(el) el.innerHTML = cfdResHtml();
}

function cfdWire(){
  const box = document.getElementById('cfdBox');
  if(!box) return;
  box.oninput = () => cfdSet(box.value);
  box.onkeydown = cfdKey;
}

function cfdHtml(){
  const k = state.cfd, c = state.cmap;
  if(!k || !c) return '';
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cfdToggle()"
      title="Type a province, a settlement or a region ID and go to it (F).
Answered out of the map you were already sent - nothing is fetched per keystroke."
      >\u{1F50D} Find${k.open ? ' ✓' : ''}</button>
    ${k.open && k.q ? `<span class="count">${k.of} match${
      k.of === 1 ? '' : 'es'}</span>` : ''}
  </div>`;
  if(!k.open) return head;
  const n = (c.man.regions || []).filter(r => r.name).length;
  return head + `<div class="cfdpanel">
    <input type="search" id="cfdBox" value="${esc(k.q)}" autocomplete="off"
      spellcheck="false" placeholder="province, settlement or region ID">
    <div id="cfdRes">${cfdResHtml()}</div>
    <div class="count">${n} province${n === 1 ? '' : 's'} on this map, each
      searchable by the words the player reads and by the code name the files
      use. Enter goes to the first one.</div>
  </div>`;
}

function cfdResHtml(){
  const k = state.cfd;
  if(!k || !k.q.trim()) return '';
  if(!k.of) return `<div class="count">Nothing on this map is called that.
    A province the file declares and never paints has no tile to go to, so it is
    not here - the read's own findings at the top of this panel list those.</div>`;
  return `<div class="cfdres">${k.hits.map((h, i) => `
    <div class="cfdrow" onclick="cfdGo(${i})" title="Go to ${esc(h.name)}">
      <b>${esc(h.shown || h.name)}</b>
      <span class="count">${esc(h.what)}${h.id >= 0 ? ` · #${h.id}` : ''}</span>
      <div class="count">${esc(h.name)}${h.settlement
        ? ` · ${esc(h.shown_settlement || h.settlement)}` : ''}${h.declared
        ? '' : ' · painted and declared nowhere'}</div>
    </div>`).join('')}
    ${k.of > k.hits.length ? `<div class="count">and ${k.of - k.hits.length}
      more - a longer word narrows it</div>` : ''}</div>`;
}
