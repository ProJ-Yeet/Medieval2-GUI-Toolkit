/* The campaign map's 3D models - 16k.

   Every other panel on this screen edits a line of text. This one does not
   edit anything: it is the one place in the toolkit where you can look at what
   the campaign map is actually made of - the settlement that stands on a
   region, the general who walks between them, the resource icons - and turn it
   around. `descr_strat.txt` names a settlement's level and its culture, and
   what the game draws for that pair is a `.cas` in `data/models_strat`; until
   now nothing here could open one.

   The viewing is Phase 15's, unchanged. This panel is the picker in front of
   it: the mod's models grouped as the folders group them, a filter box because
   Third Age Reforged ships 250 of them, and a click that hands the file to
   `v3OpenCas`. Nothing is read off the disk until somebody opens the panel,
   the way the campaign panel beside it works, because a mod's model list is a
   directory walk and this screen already does enough on load. */

function cmodNew(mod){
  return {mod, open: false, loading: false, err: '', models: null,
          filter: '', chosen: ''};
}

async function cmodOpen(force){
  const c = state.cmap;
  if(!c) return;
  const was = state.cmod;
  if(was && was.mod === c.mod && was.models && !force){ cmodPaint(); return; }
  const k = state.cmod = cmodNew(c.mod);
  k.open = was ? was.open : false;
  k.filter = was ? was.filter : '';
  if(!k.open){ cmodPaint(); return; }
  k.loading = true;
  cmodPaint();
  let d;
  try{ d = await api.get(`/api/map/models?mod=${enc(c.mod)}`); }
  catch(e){ d = {error: errText(e)}; }
  if(state.cmod !== k) return;
  k.loading = false;
  if(d.error){ k.err = d.error; cmodPaint(); return; }
  k.models = d.models || [];
  cmodPaint();
}

function cmodToggle(){
  const k = state.cmod;
  if(!k) return;
  k.open = !k.open;
  if(k.open && !k.models) cmodOpen(true); else cmodPaint();
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

function cmodShow(rel){
  const k = state.cmod;
  if(!k) return;
  k.chosen = rel;
  cmodPaint();
  v3OpenCas(k.mod, rel);
}

function cmodPaint(){
  const el = document.getElementById('cmModels');
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
  if(!k) return '';
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cmodToggle()"
      title="The models the campaign map draws - settlements, generals, agents, resources - in 3D. Nothing here changes a file."
      >\u{1F3F0} Strat models${k.open ? ' ✓' : ''}</button>
    ${k.models ? `<span class="count">${k.models.length} in this mod</span>` : ''}
    ${k.loading ? '<span class="count">reading…</span>' : ''}
  </div>`;
  if(!k.open) return head;
  if(k.loading) return head + '<div class="cxpanel count">finding the models…</div>';
  if(k.err) return head + `<div class="cxpanel w-warn">${esc(k.err)}</div>`;
  const models = k.models || [];
  if(!models.length)
    return head + `<div class="cxpanel count">this mod ships no
      <code>data/models_strat</code>, so it uses the game's own strat models</div>`;

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
  return head + `<div class="cxpanel">
    <label class="v3f"><span>Find</span>
      <input id="cmodFilter" type="text" value="${esc(k.filter)}"
        placeholder="castle, general, symbol…"
        oninput="cmodFilter(this.value)"></label>
    ${shown.length === models.length ? ''
      : `<div class="count">${shown.length} of ${models.length}</div>`}
    <div class="cmodlist">${rows || '<div class="count">nothing by that name</div>'}</div>
  </div>`;
}
