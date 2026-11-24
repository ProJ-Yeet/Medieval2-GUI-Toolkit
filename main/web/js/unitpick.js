/* 2026-11-24: the one unit picker. Armory Studio's: a search over a unit's
   type and model, and the unit editor's faction, category and class filters,
   with the rows under them repainted alone, so typing never loses its box.
   Anywhere a unit is chosen (Armory Studio's export, the card maker, its Save
   menu) it is this, never a bare drop-down.

   upkHtml(id, units, opts) returns its markup; opts:
     onPick(type)   a row taken (a click; with onPeek, a double click)
     onPeek(type)   a click, when a click only shows the unit
     current        the type marked as chosen
     tiles          cards with their picture (the unit editor's), else rows
     model(u)       the model line shown under a unit (its soldier by default)
     skip           types left out of the list
   Its filters are kept per id while the page lives. */
const UPK = new Map();
const upkQ = id => UPK.get(id) || {f: {q: '', faction: '', category: '', cls: ''}};
function upkHtml(id, units, opts){
  const st = {...upkQ(id), units: units || [], opts: opts || {}};
  UPK.set(id, st);
  const f = st.f, L = st.units, k = esc(JSON.stringify(id));
  const uniq = list => [...new Set(list.filter(Boolean))].sort((x, y) => x.localeCompare(y));
  const sel = (key, label, list) => `<select onchange="upkSet(${k},'${key}',this.value)"><option value="">${label}</option>
    ${list.map(v => `<option${f[key] === v ? ' selected' : ''}>${esc(v)}</option>`).join('')}</select>`;
  setTimeout(() => upkRows(id), 0);
  return `<div class="upk"><div class="armexprow"><input placeholder="${ttA('armory.find')}" value="${esc(f.q)}" oninput="upkSet(${k},'q',this.value)">
      ${sel('faction', tt('armory.exp_all_factions'), uniq(L.flatMap(u => u.factions || [])))}
      ${sel('category', tt('armory.exp_all_categories'), uniq(L.map(u => u.category)))}
      ${sel('cls', tt('armory.exp_all_classes'), uniq(L.map(u => u['class'])))}</div>
    <div class="${st.opts.tiles ? 'grid upktiles' : 'armexplist'}" id="upk_${esc(id)}"></div></div>`;
}
function upkSet(id, key, value){ upkQ(id).f[key] = value; upkRows(id); }
function upkRows(id){
  const el = document.getElementById('upk_' + id), st = UPK.get(id);
  if(!el || !st) return;
  const f = st.f, o = st.opts, q = (f.q || '').trim().toLowerCase(), skip = new Set(o.skip || []);
  const model = u => (o.model ? o.model(u) : u.soldier) || '';
  const rows = st.units.filter(u => !skip.has(u.type) && (!q || u.type.toLowerCase().includes(q) || model(u).toLowerCase().includes(q))
    && (!f.faction || (u.factions || []).includes(f.faction)) && (!f.category || u.category === f.category) && (!f.cls || u['class'] === f.cls));
  // a click takes the unit, or with onPeek only shows it; a double click takes it
  const k = esc(JSON.stringify(id)), t = u => esc(JSON.stringify(u.type)), take = o.onPeek ? 'false' : 'true';
  el.innerHTML = rows.slice(0, 400).map(u => o.tiles
    ? `<div class="card${u.type === o.current ? ' sel' : ''}" onclick="upkClick(${k},${t(u)},${take})" ondblclick="upkClick(${k},${t(u)},true)" title="${esc(u.type)}">
        <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src, u.type, 'card')}" alt="">
        <div class="meta"><div class="nm">${esc(u.type)}</div><div class="sub">${esc(u.category)} · ${esc(u['class'])}</div><div class="sub">${esc(model(u))}</div></div></div>`
    : `<button class="armexprowbtn${u.type === o.current ? ' on' : ''}" onclick="upkClick(${k},${t(u)},${take})" ondblclick="upkClick(${k},${t(u)},true)">
        <b>${esc(u.type)}</b> <span class="count">${esc(u.category)} · ${esc(u['class'])} · ${esc(model(u))}</span></button>`).join('')
    || `<div class="count">${tt('armory.nothing_matches')}</div>`;
}
function upkClick(id, type, take){
  const st = UPK.get(id);
  if(!st) return;
  if(!take && st.opts.onPeek){ st.opts.current = type; upkRows(id); st.opts.onPeek(type); return; }
  if(st.opts.onPick) st.opts.onPick(type);
}
