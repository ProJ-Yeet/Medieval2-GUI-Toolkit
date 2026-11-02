/* scriptblocks.js - 96f: the Module builder as blocks, Scratch style

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =========================================================================
   The same recipe the Module builder's form edits (scripts.js), drawn as
   blocks: a WHEN hat on top, an IF block whose mouth holds the condition
   bricks, a DO mouth for the actions (for each town, army or faction when
   picked) and an ELSE mouth under it. Each block carries its own boxes,
   built by the form's own sxFieldHtml, so a value typed here is the value
   the form shows; the two views are one recipe, and switching loses nothing.

   Blocks come from the palette by dragging, move between and within mouths
   by dragging, and go by dropping on the bin. The ↑ ↓ ✕ on each block do
   the same without a mouse drag. A condition only fits the IF mouth and an
   action only DO and ELSE, the way the recipe is made.
   ========================================================================= */
const SXB_TYPE = 'application/x-sxb';

function sxbGroupList(group){ return group === 'ifs' ? state.sx.vocab.conditions : state.sx.vocab.actions; }

function sxbBlockHtml(group, i, it){
  const p = sxPart(sxbGroupList(group), it.k), kind = group === 'ifs' ? 'cond' : 'act';
  const n = (state.sx.recipe[group] || []).length;
  return `<div class="sxb sxb-${kind}" draggable="true" data-g="${group}" data-i="${i}"
      ondragstart="sxbDragStart(event)" ondragover="sxbOver(event)" ondrop="sxbDrop(event)">
    <span class="sxbname">${esc(p ? p.label : it.k)}</span>
    ${p ? p.fields.map(f => sxFieldHtml(group, i, f, it)).join('') : ''}
    <span class="sxbtools">
      <button class="mini" ${i ? '' : 'disabled'} onclick="sxbMove('${group}',${i},-1)">↑</button>
      <button class="mini" ${i < n - 1 ? '' : 'disabled'} onclick="sxbMove('${group}',${i},1)">↓</button>
      <button class="mini" onclick="sxDrop('${group}',${i})">✕</button></span>
  </div>`;
}
function sxbMouthHtml(group){
  const items = state.sx.recipe[group] || [];
  return `<div class="sxbmouth" data-g="${group}" ondragover="sxbOver(event)" ondrop="sxbDrop(event)">
    ${items.map((it, i) => sxbBlockHtml(group, i, it)).join('')}
    <div class="sxbslot count">${group === 'ifs' ? tt('scripts.blocks_drop_cond') : tt('scripts.blocks_drop_act')}</div></div>`;
}
function sxbPaletteHtml(){
  const v = state.sx.vocab;
  const brick = (group, x) => `<div class="sxb sxb-${group === 'ifs' ? 'cond' : 'act'} sxbpal" draggable="true"
      data-add="${group}" data-k="${esc(x.key)}" title="${esc(x.help || '')}" ondragstart="sxbDragStart(event)"
      ondblclick="sxbAdd('${group === 'ifs' ? 'ifs' : 'dos'}','${q1(esc(x.key))}')">${esc(x.label)}</div>`;
  return `<div class="sxbpalette">
    <div class="count">${tt('scripts.blocks_palette_hint')}</div>
    <h4>${tt('scripts.blocks_conditions')}</h4>${v.conditions.map(x => brick('ifs', x)).join('')}
    <h4>${tt('scripts.blocks_actions')}</h4>${v.actions.map(x => brick('dos', x)).join('')}
    <div class="sxbbin" ondragover="sxbOver(event)" ondrop="sxbBin(event)">🗑 ${tt('scripts.blocks_bin')}</div>
  </div>`;
}
function sxBlocksHtml(){
  const s = state.sx, r = s.recipe, voc = s.vocab;
  const opt = (pairs, cur) => pairs.map(([k, l]) => `<option value="${esc(k)}" ${k === cur ? 'selected' : ''}>${esc(l)}</option>`).join('');
  return `<div class="sxblocks">${sxbPaletteHtml()}
    <div class="sxbscript">
      <div class="sxb sxb-hat"><b>${tt('scripts.when')}</b>
        <select onchange="state.sx.recipe.when=this.value;state.sx.pv=null;renderScripts()">${voc.events.map(e =>
          `<option value="${esc(e.key)}" ${e.key === r.when ? 'selected' : ''}>${esc(e.label)}</option>`).join('')}</select>
        <label class="chk"><input type="checkbox" ${r.once ? 'checked' : ''} onchange="state.sx.recipe.once=this.checked;state.sx.pv=null"> ${tt('scripts.once')}</label></div>
      <div class="sxbc sxb-ctl">
        <div class="sxbjaw"><b>${tt('scripts.if')}</b> <select onchange="state.sx.recipe.match=this.value;state.sx.pv=null">${opt(voc.match, r.match)}</select></div>
        ${sxbMouthHtml('ifs')}
        <div class="sxbjaw"><b>${tt('scripts.do')}</b> <select onchange="state.sx.recipe.each=this.value;state.sx.pv=null;renderScripts()">${opt(voc.each, r.each)}</select>
          ${r.each ? `<select onchange="state.sx.recipe.each_of=this.value;state.sx.pv=null;renderScripts()">${opt(voc.each_of, r.each_of)}</select>
            ${r.each_of === 'named' ? `<input value="${esc(r.each_faction || '')}" oninput="state.sx.recipe.each_faction=this.value">` : ''}` : ''}</div>
        ${sxbMouthHtml('dos')}
        <div class="sxbjaw"><b>${tt('scripts.else')}</b></div>
        ${sxbMouthHtml('else')}
        <div class="sxbjaw sxbfoot"></div>
      </div>
    </div></div>`;
}

/* ---- moving blocks ---- */
function sxbDragStart(ev){
  const el = ev.target.closest('.sxb');
  if(!el || ev.target.closest('input,select,textarea')) { ev.preventDefault(); return; }
  const what = el.dataset.add ? {add: el.dataset.add, k: el.dataset.k} : {g: el.dataset.g, i: +el.dataset.i};
  ev.dataTransfer.setData(SXB_TYPE, JSON.stringify(what));
  ev.dataTransfer.effectAllowed = 'move';
}
function sxbOver(ev){
  if(![...ev.dataTransfer.types].includes(SXB_TYPE)) return;
  ev.preventDefault();
  ev.stopPropagation();
}
//: which mouth and before which block a drop lands
function sxbTarget(ev){
  const mouth = ev.target.closest('.sxbmouth');
  if(!mouth) return null;
  const g = mouth.dataset.g, list = state.sx.recipe[g] || [];
  const blk = ev.target.closest('.sxb[data-i]');
  let at = list.length;
  if(blk && blk.dataset.g === g){
    const r = blk.getBoundingClientRect();
    at = +blk.dataset.i + (ev.clientY > r.top + r.height / 2 ? 1 : 0);
  }
  return {g, at};
}
//: a condition belongs in IF, an action in DO or ELSE
function sxbFits(fromGroup, toGroup){ return (fromGroup === 'ifs') === (toGroup === 'ifs'); }
function sxbDrop(ev){
  ev.preventDefault(); ev.stopPropagation();
  let what;
  try{ what = JSON.parse(ev.dataTransfer.getData(SXB_TYPE) || 'null'); }catch(e){ what = null; }
  const to = sxbTarget(ev);
  if(!what || !to) return;
  const r = state.sx.recipe;
  r[to.g] = r[to.g] || [];
  if(what.add){
    if(!sxbFits(what.add, to.g)){ toast(tt('scripts.blocks_wrong_mouth'), 3500); return; }
    const p = sxPart(sxbGroupList(to.g), what.k), it = {k: what.k};
    ((p && p.fields) || []).forEach(f => { it[f.name] = f['default']; });
    r[to.g].splice(to.at, 0, it);
  }else{
    if(!sxbFits(what.g, to.g)){ toast(tt('scripts.blocks_wrong_mouth'), 3500); return; }
    const [it] = r[what.g].splice(what.i, 1);
    let at = to.at;
    if(what.g === to.g && what.i < at) at--;
    r[to.g].splice(at, 0, it);
  }
  state.sx.pv = null;
  renderScripts();
}
function sxbBin(ev){
  ev.preventDefault(); ev.stopPropagation();
  let what;
  try{ what = JSON.parse(ev.dataTransfer.getData(SXB_TYPE) || 'null'); }catch(e){ what = null; }
  if(what && !what.add) sxDrop(what.g, what.i);
}
function sxbMove(group, i, d){
  const list = state.sx.recipe[group], j = i + d;
  if(j < 0 || j >= list.length) return;
  [list[i], list[j]] = [list[j], list[i]];
  state.sx.pv = null;
  renderScripts();
}
function sxbAdd(group, key){
  const r = state.sx.recipe, p = sxPart(sxbGroupList(group), key), it = {k: key};
  ((p && p.fields) || []).forEach(f => { it[f.name] = f['default']; });
  (r[group] = r[group] || []).push(it);
  state.sx.pv = null;
  renderScripts();
}
