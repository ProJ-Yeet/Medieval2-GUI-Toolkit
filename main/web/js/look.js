/* look.js - 96f: the toolkit's own look, set by the person using it

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   Two halves, both kept in settings.json as `ui_look`, so every start has
   them:

   APPEARANCE  the colours the whole page is drawn in (the :root variables
               index.html's styles read), one font for every screen and its
               size. Each has its own reset; an empty value is the tool's own.

   IN PLACE    a mode where a click on any button, tab, label or heading of
               the tool renames it or hides it. A piece is known by its id,
               else by what its click runs, else by its own words - what is
               stable across a repaint, which on these pages is constant. A
               MutationObserver lays the changes over every repaint, so a
               renamed button stays renamed when its screen is drawn again.
               Restore puts one piece back; Show everything again, all.
   ========================================================================= */
const LOOK_COLOURS = [['bg', '--bg'], ['panel', '--panel'], ['panel2', '--panel2'], ['edge', '--edge'],
                      ['ink', '--ink'], ['dim', '--dim'], ['accent', '--accent'], ['accent2', '--accent2']];
const LOOK_PIECES = 'button,label,legend,h1,h2,h3,.trsechead,.mftab';
let lookEditing = false, lookObserver = null;

function look(){
  const s = state.settings || (state.settings = {});
  const l = s.ui_look = s.ui_look || {};
  l.colours = l.colours || {}; l.rename = l.rename || {}; l.hide = l.hide || [];
  return l;
}
function lookSave(){ api.post('/api/settings', {ui_look: look()}); }
//: the tool's own value of a colour, read before any of ours is laid over it
function lookDefault(cssVar){
  const root = document.documentElement, mine = root.style.getPropertyValue(cssVar);
  root.style.removeProperty(cssVar);
  const v = getComputedStyle(root).getPropertyValue(cssVar).trim();
  if(mine) root.style.setProperty(cssVar, mine);
  return v;
}
function lookApply(){
  const l = look(), root = document.documentElement;
  for(const [k, v] of LOOK_COLOURS){
    if(l.colours[k]) root.style.setProperty(v, l.colours[k]); else root.style.removeProperty(v);
  }
  if(l.font) root.style.setProperty('--ui-font', l.font); else root.style.removeProperty('--ui-font');
  document.body.style.fontSize = l.size ? l.size + 'px' : '';
  lookPieces(document.body);
  if(!lookObserver){
    lookObserver = new MutationObserver(muts => {
      if(!Object.keys(look().rename).length && !look().hide.length && !lookEditing) return;
      for(const m of muts) for(const n of m.addedNodes) if(n.nodeType === 1) lookPieces(n);
    });
    lookObserver.observe(document.body, {childList: true, subtree: true});
  }
}

/* ---- the pieces ---- */
function lookKey(el){
  if(el.dataset.lookKey) return el.dataset.lookKey;
  const words = (el.dataset.lookOrig != null ? el.dataset.lookOrig : el.textContent).trim().slice(0, 60);
  const key = el.id ? '#' + el.id
    : el.getAttribute('onclick') ? el.tagName.toLowerCase() + '@' + el.getAttribute('onclick')
    : el.tagName.toLowerCase() + ':' + words;
  el.dataset.lookKey = key;
  return key;
}
//: the text node a piece's words are in: its own, past any icon
function lookTextNode(el){
  const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  let n;
  while((n = w.nextNode())) if(n.nodeValue.trim()) return n;
  return null;
}
function lookPieces(root){
  const l = look();
  const hide = new Set(l.hide), names = l.rename;
  // with nothing set, only the pieces changed before are visited, to put them back
  const none = !hide.size && !Object.keys(names).length && !lookEditing;
  if(none && !(root.querySelector && root.querySelector('[data-look-orig],.look-hidden'))) return;
  const all = root.matches && root.matches(LOOK_PIECES) ? [root] : [];
  for(const el of root.querySelectorAll ? root.querySelectorAll(LOOK_PIECES) : []) all.push(el);
  for(const el of all){
    if(el.closest('#lookBar,#lookPop')) continue;
    const key = lookKey(el);
    el.classList.toggle('look-hidden', hide.has(key));
    const t = lookTextNode(el);
    if(!t) continue;
    if(el.dataset.lookOrig == null) el.dataset.lookOrig = t.nodeValue;
    const want = names[key] != null ? names[key] : el.dataset.lookOrig;
    if(t.nodeValue !== want) t.nodeValue = want;
  }
}

/* ---- editing in place ---- */
function lookEdit(on){
  lookEditing = !!on;
  document.body.classList.toggle('look-editing', lookEditing);
  let bar = document.getElementById('lookBar');
  if(lookEditing && !bar){
    bar = document.createElement('div');
    bar.id = 'lookBar';
    bar.className = 'lookbar';
    document.body.appendChild(bar);
  }
  if(bar){
    bar.style.display = lookEditing ? '' : 'none';
    bar.innerHTML = `${tt('look.editing_bar')}
      <button onclick="lookShowAll()">${tt('look.show_all')}</button>
      <button class="primary" onclick="lookEdit(false)">${tt('look.done')}</button>`;
  }
  lookPop(null);
  lookPieces(document.body);
}
document.addEventListener('click', ev => {
  if(!lookEditing) return;
  if(ev.target.closest('#lookBar,#lookPop')) return;
  const el = ev.target.closest(LOOK_PIECES);
  if(!el) return;
  ev.preventDefault(); ev.stopPropagation();
  lookPop(el);
}, true);
function lookPop(el){
  let pop = document.getElementById('lookPop');
  if(!el){ if(pop) pop.remove(); return; }
  if(!pop){
    pop = document.createElement('div');
    pop.id = 'lookPop';
    pop.className = 'lookpop';
    document.body.appendChild(pop);
  }
  const key = lookKey(el), l = look(), t = lookTextNode(el);
  const now = l.rename[key] != null ? l.rename[key] : (el.dataset.lookOrig || (t ? t.nodeValue : ''));
  pop.dataset.key = key;
  pop.innerHTML = `<div class="count">${esc(el.dataset.lookOrig || '').trim() || esc(key)}</div>
    ${t ? `<input id="lookName" value="${esc(now.trim())}">` : ''}
    <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">
      ${t ? `<button class="primary" onclick="lookRename()">${tt('look.rename')}</button>` : ''}
      <button onclick="lookHide()">${l.hide.includes(key) ? tt('look.unhide') : tt('look.hide')}</button>
      <button onclick="lookRestore()">${tt('look.restore')}</button>
      <button onclick="lookPop(null)">${tt('common.cancel')}</button></div>`;
  const r = el.getBoundingClientRect();
  pop.style.left = Math.max(4, Math.min(r.left, innerWidth - 280)) + 'px';
  pop.style.top = Math.min(r.bottom + 4, innerHeight - 120) + 'px';
  const box = document.getElementById('lookName');
  if(box){ box.focus(); box.select(); box.onkeydown = e => { if(e.key === 'Enter') lookRename(); }; }
}
function lookPopKey(){ const p = document.getElementById('lookPop'); return p ? p.dataset.key : ''; }
function lookRename(){
  const key = lookPopKey(), v = (document.getElementById('lookName') || {}).value;
  if(!key || v == null) return;
  const l = look();
  if(v.trim()) l.rename[key] = ' ' + v.trim() + ' '; else delete l.rename[key];
  lookSave(); lookPop(null); lookPieces(document.body);
}
function lookHide(){
  const key = lookPopKey(), l = look();
  if(!key) return;
  l.hide = l.hide.includes(key) ? l.hide.filter(k => k !== key) : l.hide.concat([key]);
  lookSave(); lookPop(null); lookPieces(document.body);
}
function lookRestore(){
  const key = lookPopKey(), l = look();
  if(!key) return;
  delete l.rename[key]; l.hide = l.hide.filter(k => k !== key);
  lookSave(); lookPop(null); lookPieces(document.body);
}
function lookShowAll(){
  const l = look();
  if(!confirm(tt('look.show_all_confirm', {n: Object.keys(l.rename).length + l.hide.length}))) return;
  l.rename = {}; l.hide = [];
  lookSave(); lookPieces(document.body);
}

/* ---- Appearance, in Settings ---- */
function lookSettingsHtml(){
  const l = look();
  const names = LOOK_LABELS();
  const row = ([k, v]) => `<label class="lookcol">${esc(names[k] || k)}
    <input type="color" value="${esc(l.colours[k] || lookHex(lookDefault(v)))}" onchange="lookColour('${k}', this.value)">
    ${l.colours[k] ? `<button class="mini" title="${ttA('look.reset')}" onclick="lookColour('${k}', '')">↺</button>` : ''}</label>`;
  return `<fieldset><legend>${tt('look.appearance')}</legend>
    <div class="lookcols">${LOOK_COLOURS.map(row).join('')}</div>
    <label style="display:block;margin-top:8px">${tt('look.font')}
      <input value="${esc(l.font || '')}" placeholder="${esc(getComputedStyle(document.body).fontFamily.split(',')[0].replace(/"/g, ''))}" style="width:200px" onchange="lookSet('font', this.value.trim())"></label>
    <label style="display:block;margin-top:6px">${tt('look.size')}
      <input type="number" min="10" max="22" value="${esc(l.size || '')}" placeholder="14" style="width:70px"
        onchange="lookSet('size', +this.value || 0)"></label>
    <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
      <button onclick="closeModal();lookEdit(true)">${tt('look.edit_in_place')}</button>
      <button onclick="lookAllBack()">${tt('look.all_back')}</button></div>
    <div class="count" style="margin-top:6px">${ttN('look.hint', Object.keys(l.rename).length + l.hide.length)}</div>
  </fieldset>`;
}
const LOOK_LABELS = () => ({bg: tt('look.colour_bg'), panel: tt('look.colour_panel'), panel2: tt('look.colour_panel2'),
  edge: tt('look.colour_edge'), ink: tt('look.colour_ink'), dim: tt('look.colour_dim'),
  accent: tt('look.colour_accent'), accent2: tt('look.colour_accent2')});
function lookHex(css){
  const m = /^#([0-9a-f]{6})$/i.exec(css || '');
  if(m) return css;
  const s = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(css || '');
  return s ? '#' + s[1] + s[1] + s[2] + s[2] + s[3] + s[3] : '#000000';
}
function lookColour(k, v){ look().colours[k] = v; if(!v) delete look().colours[k]; lookSave(); lookApply(); lookRepaintSettings(); }
function lookSet(k, v){ look()[k] = v; lookSave(); lookApply(); }
function lookAllBack(){
  const l = look();
  l.colours = {}; l.font = ''; l.size = 0;
  lookSave(); lookApply(); lookRepaintSettings();
}
function lookRepaintSettings(){
  const el = document.getElementById('lookSettings');
  if(el) el.innerHTML = lookSettingsHtml();
}
