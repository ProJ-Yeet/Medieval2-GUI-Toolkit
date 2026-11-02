/* artbrowse.js - 96f: every picture in the mod, kind by kind

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   The art browser, a third view of the Unit cards tab

   Every other screen shows a picture where it is used. This one answers
   "what pictures does this mod have?": the server (unittransfer/artbrowse.py)
   sorts every loose .tga / .dds under data/ by the folder the game reads it
   from, and this lists them kind by kind as thumbnails. A right click on any
   of them is images.js's menu - Replace, Open file location - so nothing
   here writes on its own.

   The filter repaints only the grid under it, never the box being typed in.
   ========================================================================= */
const ART_PAGE = 120;
//: each kind's name, spelled out so every ID is written where it is used
const ART_KIND_LABEL = () => ({
  unit_cards: tt('artbrowse.kind_unit_cards'),
  unit_info: tt('artbrowse.kind_unit_info'),
  buildings: tt('artbrowse.kind_buildings'),
  portraits: tt('artbrowse.kind_portraits'),
  ancillaries: tt('artbrowse.kind_ancillaries'),
  events: tt('artbrowse.kind_events'),
  pips: tt('artbrowse.kind_pips'),
  resources: tt('artbrowse.kind_resources'),
  settlements: tt('artbrowse.kind_settlements'),
  interface_pages: tt('artbrowse.kind_interface_pages'),
  campaign: tt('artbrowse.kind_campaign'),
  map: tt('artbrowse.kind_map'),
  loading: tt('artbrowse.kind_loading'),
  symbols: tt('artbrowse.kind_symbols'),
  menu: tt('artbrowse.kind_menu'),
  interface: tt('artbrowse.kind_interface'),
  other: tt('artbrowse.kind_other'),
});

async function loadArtBrowse(refresh){
  const mod = state.src;
  main.innerHTML = bmdbTabsHtml(tt('artbrowse.note')) + cardsSubTabsHtml()
    + `<div class="empty">${tt('artbrowse.reading')}</div>`;
  let r;
  try{ r = await api.get(`/api/artbrowse?mod=${enc(mod)}${refresh ? '&refresh=1' : ''}`); }
  catch(e){ r = {error: errText(e)}; }
  if(state.mode !== 'cards' || state.src !== mod) return;
  const keep = state.art && state.art.mod === mod ? state.art.kind : '';
  state.art = Object.assign({mod, kind: '', q: '', rows: [], count: 0, ask: 0}, r);
  state.art.kind = (r.kinds || []).some(k => k.kind === keep) ? keep : ((r.kinds || [])[0] || {}).kind || '';
  renderArtBrowse();
  if(state.art.kind) artLoadKind(state.art.kind);
}

function renderArtBrowse(){
  const a = state.art;
  if(!a || a.mod !== state.src) return loadArtBrowse();
  if(a.error){ main.innerHTML = bmdbTabsHtml() + cardsSubTabsHtml()
    + `<div class="empty w-bad">✗ ${esc(a.error)}</div>`; return; }
  count.textContent = ttN('artbrowse.pictures', a.total || 0);
  main.innerHTML = bmdbTabsHtml(tt('artbrowse.note')) + cardsSubTabsHtml() + `
    <div class="artbrowse">
      <div class="artkinds">${(a.kinds || []).map(k => `<button class="artkind${k.kind === a.kind ? ' on' : ''}"
          onclick="artLoadKind('${q1(esc(k.kind))}')">${esc(ART_KIND_LABEL()[k.kind] || k.kind)}
          <span class="count">${k.count}</span></button>`).join('')}
        <button onclick="loadArtBrowse(true)" style="margin-top:8px">${tt('artbrowse.refresh')}</button></div>
      <div class="artmain">
        <div class="artbar"><input id="artQ" placeholder="${ttA('artbrowse.filter')}" value="${esc(a.q)}"
          oninput="artFilter(this.value)"> <span class="count" id="artCount"></span></div>
        <div class="count">${tt('artbrowse.hint')}</div>
        <div id="artGrid" class="artgrid"></div>
      </div>
    </div>`;
  artPaintGrid();
}

function artPaintGrid(){
  const a = state.art, el = document.getElementById('artGrid');
  if(!el) return;
  document.getElementById('artCount').textContent = a.busy ? tt('common.reading')
    : ttN('artbrowse.shown', a.rows.length, {total: a.count});
  el.innerHTML = a.rows.map(f => `<figure class="artcell" title="${esc(f.rel)}">
      <img loading="lazy" alt="" src="/icon?mod=${enc(a.mod)}&kind=modfile&rel=${enc(f.rel)}${iconBust()}"
        onerror="this.classList.add('gone')">
      <figcaption>${esc(f.rel.split('/').pop())}</figcaption></figure>`).join('')
    + (a.rows.length < a.count ? `<div class="artmore"><button onclick="artMore()">${
        tt('artbrowse.more', {n: Math.min(ART_PAGE, a.count - a.rows.length)})}</button></div>` : '');
}

async function artFetch(offset){
  const a = state.art;
  return api.get(`/api/artbrowse/files?mod=${enc(a.mod)}&kind=${enc(a.kind)}&q=${enc(a.q)}&offset=${offset}&limit=${ART_PAGE}`);
}
async function artLoadKind(kind){
  const a = state.art;
  if(!a) return;
  const first = a.kind !== kind || !document.getElementById('artGrid');
  a.kind = kind; a.rows = []; a.count = 0; a.busy = true;
  if(first) renderArtBrowse(); else artPaintGrid();
  const ask = ++a.ask;
  let r;
  try{ r = await artFetch(0); }catch(e){ r = {files: [], count: 0, error: errText(e)}; }
  if(state.art !== a || a.ask !== ask) return;
  a.busy = false; a.rows = r.files || []; a.count = r.count || 0;
  if(r.error) toast('✗ ' + r.error, 5000);
  artPaintGrid();
}
let artTimer = 0;
function artFilter(v){
  state.art.q = v;
  clearTimeout(artTimer);
  artTimer = setTimeout(() => artLoadKind(state.art.kind), 250);
}
async function artMore(){
  const a = state.art;
  let r;
  try{ r = await artFetch(a.rows.length); }catch(e){ toast('✗ ' + errText(e), 5000); return; }
  if(state.art !== a) return;
  a.rows = a.rows.concat(r.files || []);
  artPaintGrid();
}
