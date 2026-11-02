/* menusheets.js - 96f: the game's menu pictures, page by page

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   Menu sheets, a fourth view of the Unit cards tab

   The interface's pictures are named boxes on the pages of four sprite
   sheets (unittransfer/menusheets.py). A sheet and a culture are picked, then
   a page; the page is drawn with every sprite's box over it, and a click on a
   box picks that sprite: its name and box, Save as PNG, and Replace, which
   paints a picture into the box on this culture's page (stretched, kept in
   shape or filling it), backed up and undoable from the Log. Find looks
   through every sheet's names and repaints only the list under it.
   ========================================================================= */

async function loadMenuSheets(){
  const mod = state.src;
  main.innerHTML = bmdbTabsHtml(tt('menusheets.note')) + cardsSubTabsHtml()
    + `<div class="empty">${tt('menusheets.reading')}</div>`;
  let r;
  try{ r = await api.get(`/api/menusheets?mod=${enc(mod)}`); }
  catch(e){ r = {error: errText(e)}; }
  if(state.mode !== 'cards' || state.src !== mod) return;
  const old = state.ms && state.ms.mod === mod ? state.ms : {};
  const sheets = r.sheets || [], cults = r.cultures || [];
  state.ms = Object.assign({mod, q: '', pick: '', fit: 'stretch', stamp: Date.now()}, r);
  state.ms.sheet = sheets.some(s => s.rel === old.sheet) ? old.sheet : ((sheets[0] || {}).rel || '');
  state.ms.culture = cults.includes(old.culture) ? old.culture : (cults[0] || '');
  state.ms.page = old.sheet === state.ms.sheet ? (old.page || 0) : 0;
  renderMenuSheets();
}

const msSheet = () => (state.ms.sheets || []).find(s => s.rel === state.ms.sheet) || null;

function renderMenuSheets(){
  const m = state.ms;
  if(!m || m.mod !== state.src) return loadMenuSheets();
  if(m.error || !(m.sheets || []).length){ main.innerHTML = bmdbTabsHtml() + cardsSubTabsHtml()
    + `<div class="empty w-bad">✗ ${esc(m.error || tt('menusheets.none'))}</div>`; return; }
  const s = msSheet();
  count.textContent = ttN('menusheets.sprites', s.sprites.length);
  main.innerHTML = bmdbTabsHtml(tt('menusheets.note')) + cardsSubTabsHtml() + `
    <div class="artbar">
      <select onchange="msSet('sheet', this.value)">${m.sheets.map(x =>
        `<option value="${esc(x.rel)}"${x.rel === m.sheet ? ' selected' : ''}>${esc(x.rel)}</option>`).join('')}</select>
      <select onchange="msSet('culture', this.value)" title="${ttA('menusheets.culture_title')}">${(m.cultures || []).map(c =>
        `<option value="${esc(c)}"${c === m.culture ? ' selected' : ''}>${esc(c)}</option>`).join('')}</select>
      <input id="msQ" placeholder="${ttA('menusheets.find')}" value="${esc(m.q)}" oninput="msFind(this.value)">
    </div>
    <div id="msFound"></div>
    <div class="artbrowse">
      <div class="artkinds">${s.pages.map((p, i) => `<button class="artkind${i === m.page ? ' on' : ''}"
          onclick="msSet('page', ${i})">${esc(p)} <span class="count">${s.sprites.filter(x => x.page === i).length}</span></button>`).join('')}</div>
      <div class="artmain">
        <div class="count" id="msWhere">${tt('menusheets.hint')}</div>
        <div class="mspage" id="msPage"></div>
        <div id="msPick"></div>
      </div>
    </div>`;
  msPaintFound();
  msPaintPage();
}

function msSet(k, v){
  const m = state.ms;
  m[k] = k === 'page' ? +v : v;
  if(k === 'sheet'){ m.page = 0; m.pick = ''; }
  renderMenuSheets();
}

/* --- the page, its boxes, the sprite picked ------------------------------- */

function msPageUrl(){
  const m = state.ms, s = msSheet();
  return `/api/menusheets/page?mod=${enc(m.mod)}&culture=${enc(m.culture)}&page=${enc(s.pages[m.page] || '')}&t=${m.stamp}`;
}

async function msPaintPage(){
  const host = document.getElementById('msPage');
  if(!host) return;
  const m = state.ms, s = msSheet(), url = msPageUrl();
  host.innerHTML = `<div class="count">${tt('menusheets.reading')}</div>`;
  let where = '';
  try{
    const res = await fetch(url);
    if(!res.ok){ let msg = '' + res.status; try{ msg = (await res.json()).error || msg; }catch(e){}
      host.innerHTML = `<div class="w-warn">${esc(msg)}</div>`; m.img = null; return msPaintPick(); }
    where = res.headers.get('X-Picture') || '';
  }catch(e){ host.innerHTML = `<div class="w-bad">${esc(errText(e))}</div>`; return; }
  const img = new Image();
  img.onload = () => {
    if(document.getElementById('msPage') !== host) return;
    m.img = img;
    const W = img.naturalWidth, H = img.naturalHeight;
    host.innerHTML = `<div class="mspagebox" style="aspect-ratio:${W}/${H};max-width:${Math.max(W, 512)}px">
      <img src="${url}" alt="">${s.sprites.map(x => x.page !== m.page ? '' : `<div class="msbox${x.name === m.pick ? ' on' : ''}"
        style="left:${x.box[0] / W * 100}%;top:${x.box[1] / H * 100}%;width:${(x.box[2] - x.box[0]) / W * 100}%;height:${(x.box[3] - x.box[1]) / H * 100}%"
        title="${esc(x.name)}" onclick="msPick('${q1(esc(x.name))}')"></div>`).join('')}</div>`;
    const w = document.getElementById('msWhere');
    if(w) w.textContent = where === 'game' ? tt('menusheets.from_game', {w: W, h: H}) : tt('menusheets.from_mod', {w: W, h: H});
    msPaintPick();
  };
  img.src = url;
}

function msPick(name){
  state.ms.pick = name;
  document.querySelectorAll('#msPage .msbox').forEach(el => el.classList.toggle('on', el.title === name));
  msPaintPick();
}

function msSprite(){ const s = msSheet(); return s && s.sprites.find(x => x.name === state.ms.pick) || null; }

/* The sprite cut out of the page, as a canvas. */
function msCrop(x){
  const img = state.ms.img, c = document.createElement('canvas');
  c.width = Math.max(1, x.box[2] - x.box[0]); c.height = Math.max(1, x.box[3] - x.box[1]);
  if(img) c.getContext('2d').drawImage(img, x.box[0], x.box[1], c.width, c.height, 0, 0, c.width, c.height);
  return c;
}

function msPaintPick(){
  const host = document.getElementById('msPick');
  if(!host) return;
  const x = msSprite(), m = state.ms;
  if(!x || x.page !== m.page){ host.innerHTML = ''; return; }
  const w = x.box[2] - x.box[0], h = x.box[3] - x.box[1];
  host.innerHTML = `<div class="mspick">
    <div class="mscrop" id="msCrop"></div>
    <div><b>${esc(x.name)}</b>
      <div class="count">${tt('menusheets.box', {left: x.box[0], top: x.box[1], w, h})}</div>
      <div class="row" style="margin-top:6px">
        <button onclick="msSave()" ${m.img ? '' : 'disabled'}>${tt('menusheets.save_png')}</button>
        <select onchange="state.ms.fit=this.value" title="${ttA('menusheets.fit_title')}">${[['stretch', tt('menusheets.fit_stretch')], ['keep', tt('menusheets.fit_keep')], ['fill', tt('menusheets.fit_fill')]].map(([f, label]) =>
          `<option value="${f}"${f === m.fit ? ' selected' : ''}>${label}</option>`).join('')}</select>
        <button onclick="msReplacePick()">${tt('menusheets.replace')}</button>
        <input type="file" id="msFile" accept="image/*" style="display:none" onchange="msReplace(this)">
      </div>
      <div class="count">${tt('menusheets.replace_note', {culture: esc(m.culture)})}</div>
    </div></div>`;
  if(m.img) document.getElementById('msCrop').appendChild(msCrop(x));
}

function msSave(){
  const x = msSprite();
  if(!x) return;
  const a = document.createElement('a');
  a.href = msCrop(x).toDataURL('image/png');
  a.download = `${x.name}.png`;
  a.click();
}

function msReplacePick(){ const i = document.getElementById('msFile'); if(i){ i.value = ''; i.click(); } }

async function msReplace(input){
  const f = input.files && input.files[0], x = msSprite(), m = state.ms;
  if(!f || !x) return;
  if(!confirm(tt('menusheets.replace_confirm', {name: x.name, culture: m.culture, page: msSheet().pages[x.page]}))) return;
  const b64 = await new Promise(res => { const r = new FileReader(); r.onload = () => res(String(r.result).split(',')[1] || ''); r.readAsDataURL(f); });
  let r;
  try{ r = await api.post('/api/menusheets/replace', {mod: m.mod, sheet: m.sheet, culture: m.culture, name: x.name, b64, fit: m.fit}); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error){ alert(r.error); return; }
  activity(tt('menusheets.replaced'), `${x.name} · ${m.culture}`);
  m.stamp = Date.now();
  msPaintPage();
}

/* --- Find, every sheet's names --------------------------------------------- */

function msFind(v){ state.ms.q = v; msPaintFound(); }

function msPaintFound(){
  const host = document.getElementById('msFound');
  if(!host) return;
  const q = (state.ms.q || '').trim().toLowerCase();
  if(!q){ host.innerHTML = ''; return; }
  const hits = [];
  (state.ms.sheets || []).forEach(s => s.sprites.forEach(x => {
    if(x.name.toLowerCase().includes(q)) hits.push({s, x});
  }));
  host.innerHTML = `<div class="count">${ttN('menusheets.found', hits.length)}</div>
    <div class="msfound">${hits.slice(0, 60).map(({s, x}) => `<button onclick="msGo('${q1(esc(s.rel))}', ${x.page}, '${q1(esc(x.name))}')"
      >${esc(x.name)} <span class="count">${esc(s.rel.split('/').pop())} · ${esc(s.pages[x.page] || '')}</span></button>`).join('')}</div>`;
}

function msGo(sheet, page, name){
  Object.assign(state.ms, {sheet, page, pick: name});
  renderMenuSheets();
}
