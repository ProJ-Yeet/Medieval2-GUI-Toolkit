/* hovercard.js - 96f: hover a unit or building's small picture for its card

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   Every list that names a unit or a building already draws its small
   picture through `/icon?...&type=` or `/building_icon?...`. Resting the
   mouse on one for a moment shows the card big - a unit's card and its info
   picture side by side, a building's small and constructed pictures - and
   says whose picture it is: the server names the file it sent (X-Picture),
   so a card borrowed from another faction's folder, or the game's own,
   says so.

   One floating element and one delegated listener, so it works in lists
   drawn long after this file loaded and costs nothing until a hover. A
   picture already drawn large is left alone.
   ========================================================================= */
const HC_DELAY = 350, HC_SMALL = 120;
let hcTimer = 0, hcFor = null, hcAsk = 0;

function hcEl(){
  let el = document.getElementById('hoverCard');
  if(!el){
    el = document.createElement('div');
    el.id = 'hoverCard';
    el.className = 'hovercard';
    document.body.appendChild(el);
  }
  return el;
}
function hcHide(){
  clearTimeout(hcTimer); hcFor = null; hcAsk++;
  const el = document.getElementById('hoverCard');
  if(el) el.style.display = 'none';
}
//: the URL with one query value changed
function hcWith(src, key, value){
  const u = new URL(src, location.href);
  u.searchParams.set(key, value);
  return u.pathname + u.search;
}
async function hcPicture(url){
  const r = await fetch(url);
  const blob = await r.blob();
  return {url: URL.createObjectURL(blob), where: r.headers.get('X-Picture') || ''};
}
function hcWhere(where){
  if(where === 'game') return tt('hovercard.from_game');
  if(!where) return tt('hovercard.none');
  return where;
}
async function hcShow(img, x, y){
  const ask = ++hcAsk, src = img.getAttribute('src') || '';
  const u = new URL(src, location.href);
  let parts = [], title = '';
  try{
    if(u.pathname === '/icon'){
      title = u.searchParams.get('type') || '';
      const [card, info] = await Promise.all([hcPicture(hcWith(src, 'kind', 'card')),
                                              hcPicture(hcWith(src, 'kind', 'info'))]);
      parts = [[card, tt('hovercard.card')], [info, tt('hovercard.info')]];
    }else{
      title = u.searchParams.get('level') || '';
      const [small, big] = await Promise.all([hcPicture(hcWith(src, 'kind', 'small')),
                                              hcPicture(hcWith(src, 'kind', 'large'))]);
      parts = [[small, tt('hovercard.small')], [big, tt('hovercard.constructed')]];
    }
  }catch(e){ return; }
  if(ask !== hcAsk) return;
  const el = hcEl();
  el.innerHTML = `<div class="hctitle">${esc(title)}</div><div class="hcrow">${parts.map(([p, label]) =>
    `<figure><img src="${p.url}" alt=""><figcaption>${esc(label)}<br><span class="count">${
      esc(u.pathname === '/icon' ? hcWhere(p.where) : '')}</span></figcaption></figure>`).join('')}</div>`;
  el.style.display = 'block';
  const w = el.offsetWidth, h = el.offsetHeight;
  el.style.left = Math.max(4, Math.min(x + 18, innerWidth - w - 8)) + 'px';
  el.style.top = Math.max(4, Math.min(y + 18, innerHeight - h - 8)) + 'px';
}
document.addEventListener('mouseover', ev => {
  const img = ev.target;
  if(!(img instanceof HTMLImageElement) || img.closest('#hoverCard')) return;
  const src = img.getAttribute('src') || '';
  const unit = src.startsWith('/icon?') && /[?&]type=/.test(src);
  if(!unit && !src.startsWith('/building_icon?')) return;
  if(img.getBoundingClientRect().width >= HC_SMALL) return;
  if(hcFor === img) return;
  hcHide(); hcFor = img;
  const x = ev.clientX, y = ev.clientY;
  hcTimer = setTimeout(() => { if(hcFor === img) hcShow(img, x, y); }, HC_DELAY);
});
document.addEventListener('mouseout', ev => { if(ev.target === hcFor) hcHide(); });
document.addEventListener('scroll', hcHide, true);
