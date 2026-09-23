/* heroabilities.js - Hero abilities: descr_hero_abilities.xml

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ========================= HERO ABILITIES (66) =========================
   A named character's battle ability: the name a descr_strat.txt line gives
   it (`hero_ability The_Heart_of_the_Lion`), how long it lasts and how often,
   its button, tooltip and sound, and its effects on the armies. The people
   panel's Hero ability field offers what this file declares and opens it
   here.

   THE PAGE NEVER PARSES A GAME FILE: /api/heroabilities and its plan|apply. */

async function loadHeroAbilities(){
  const mod = state.src;
  main.innerHTML = '<div class="empty">Reading ' + esc(mod) + '’s hero abilities…</div>';
  let r;
  try{ r = await api.get('/api/heroabilities?mod=' + enc(mod)); }
  catch(e){ if(stale('heroabilities', mod)) return;
    main.innerHTML = `<div class="empty">Couldn't read them.<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadHeroAbilities()">Retry</button></div>`; return; }
  if(stale('heroabilities', mod)) return;
  const keep = state.hax && state.hax.mod === mod ? state.hax : null;
  state.hax = Object.assign({mod, sel: keep ? keep.sel : '', w: haxBlank(), busy: false}, r);
  const list = r.abilities || [];
  if(!list.some(a => String(a.id) === state.hax.sel))
    state.hax.sel = list.length ? String((list.find(a => a.used_count) || list[0]).id) : '';
  renderHeroAbilities();
}
function haxBlank(){ return {values: {}, remove: [], copy: [], add_field: []}; }
function haxChanged(){
  const w = state.hax.w;
  return Object.keys(w.values).length + w.remove.length + w.copy.length + w.add_field.length;
}

function renderHeroAbilities(){
  const c = state.hax;
  if(!c){ loadHeroAbilities(); return; }
  const strip = minorTabsHtml('', 'data/descr_hero_abilities.xml');
  const find = (c.findings || []).map(f => Object.assign({}, f, {name: f.key}));
  const n = haxChanged();
  const left = c.error ? `<div class="count" style="padding:8px">${esc(c.error)}.</div>`
    : (c.abilities || []).map(a => `<button class="trrow${c.sel === String(a.id) ? ' on' : ''}" onclick="haxPick('${a.id}')">
        <div class="nm">${esc(a.name || '(no name)')}${c.w.remove.includes(a.id) ? ' <span class="count">removed on save</span>' : ''}</div>
        <div class="sub">${a.effects.length} effect(s) · ${a.used_count ? `${a.used_count} character line(s)` : 'given to nobody'}${haxDirty(a) ? ' · <b>changed</b>' : ''}</div></button>`).join('')
      + c.w.copy.filter(x => x.name).map(x => `<div class="trnote">+ ${esc(x.name)} <span class="count">on save</span></div>`).join('');
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('heroabilities', find, 'haxOpen')}
      <div class="trrows">${left}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div><b>descr_hero_abilities.xml</b> <span class="count">a named character's ability in battle</span></div>
        <span style="flex:1"></span>
        <button onclick="haxRevert()" ${n ? '' : 'disabled'}>Revert</button>
        <button class="primary" onclick="haxSave()" ${n ? '' : 'disabled'}>Save ${n || ''} change${n === 1 ? '' : 's'}</button>
      </div>
      ${c.error ? '' : haxAbilityHtml()}
    </div>
  </div>`;
}

function haxAbility(){ const c = state.hax; return (c.abilities || []).find(a => String(a.id) === c.sel); }
function haxDirty(a){
  const w = state.hax.w, ids = new Set([a.id, ...a.fields.map(f => f.id), ...a.effects.flatMap(e => [e.id, ...e.fields.map(f => f.id)])]);
  if(a.effects_id != null) ids.add(a.effects_id);
  return Object.keys(w.values).some(k => ids.has(+k)) || w.remove.some(k => ids.has(k))
    || w.copy.some(x => ids.has(x.like) || ids.has(x.into)) || w.add_field.some(x => ids.has(x.parent));
}
function haxPick(id){ state.hax.sel = String(id); renderHeroAbilities(); }
function haxOpen(key){
  const [kind, rest] = String(key).split(/\/(.*)/);
  const c = state.hax, list = c.abilities || [];
  if(kind === 'ability') c.sel = rest;
  else if(kind === 'name' || kind === 'use'){
    const a = list.find(x => x.name.toLowerCase() === String(rest).toLowerCase());
    if(a) c.sel = String(a.id);
    else if(kind === 'use') toast(`${rest} is named by a character and declared nowhere in this file.`, 6000);
  }
  renderHeroAbilities();
}
function haxRevert(){ state.hax.w = haxBlank(); renderHeroAbilities(); }

function haxVal(id, v){ const w = state.hax.w.values; return w[id] !== undefined ? w[id] : v; }
function haxSet(id, v, was){
  const w = state.hax.w.values;
  if(v.trim() === was) delete w[id]; else w[id] = v.trim();
  renderHeroAbilities();
}
/* One value box. Where the file's sample names every value the field can
   take it is a picker, so a typo cannot reach the save. */
function haxBox(f, width){
  const c = state.hax, v = haxVal(f.id, f.value), was = q1(esc(f.value));
  const pick = f.tag === 'target' ? c.targets : f.tag === 'morale_level' ? c.morale_levels
    : f.tag === 'permanent' ? ['true', 'false'] : null;
  if(pick){
    const opts = pick.includes(v) ? pick : [v, ...pick];
    return `<select onchange="haxSet(${f.id}, this.value, '${was}')">${opts.map(o =>
      `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
  }
  return `<input style="width:${width}px" value="${esc(v)}" onchange="haxSet(${f.id}, this.value, '${was}')">`;
}
function haxDrop(id){
  const r = state.hax.w.remove, i = r.indexOf(id);
  if(i >= 0) r.splice(i, 1); else r.push(id);
  renderHeroAbilities();
}

function haxFieldRows(fields, fixed){
  const w = state.hax.w, c = state.hax;
  return fields.map(f => {
    const gone = w.remove.includes(f.id);
    const text = /_tooltip_label$/.test(f.tag) && f.value ? c.labels[f.value] : undefined;
    return `<tr${gone ? ' style="opacity:.45"' : ''}><td><code>${esc(f.tag)}</code></td>
      <td>${haxBox(f, /label|sprite/.test(f.tag) ? 330 : f.tag === 'name' ? 240 : 90)}${text === null
        ? ' <span class="count">⚠ not in expanded.txt</span>' : text ? ` <span class="count">“${esc(text)}”</span>` : ''}</td>
      <td>${fixed.includes(f.tag) ? '' : `<button onclick="haxDrop(${f.id})">${gone ? 'keep' : '✕'}</button>`}</td></tr>`;
  }).join('');
}
function haxAddFieldHtml(parent, have, known, key){
  const w = state.hax.w;
  const want = known.filter(t => !have.includes(t) && !w.add_field.some(x => x.parent === parent && x.tag === t));
  const pending = w.add_field.filter(x => x.parent === parent).map(x =>
    `<tr><td><code>${esc(x.tag)}</code></td><td>${esc(x.value)} <span class="count">added on save</span></td><td></td></tr>`).join('');
  return pending + (want.length ? `<tr><td><select id="haxAddTag${key}">${want.map(t => `<option>${esc(t)}</option>`).join('')}</select></td>
    <td><input id="haxAddVal${key}" style="width:200px" placeholder="value"> <button onclick="haxAddField(${parent}, '${key}')">＋ Add</button></td><td></td></tr>` : '');
}
function haxAddField(parent, key){
  const tag = document.getElementById('haxAddTag' + key).value;
  const value = (document.getElementById('haxAddVal' + key).value || '').trim();
  if(!value) return toast('Give the new field a value first.');
  state.hax.w.add_field.push({parent, tag, value});
  renderHeroAbilities();
}

function haxAbilityHtml(){
  const c = state.hax, a = haxAbility();
  if(!a) return '<div class="count" style="padding:8px">Pick an ability.</div>';
  const w = c.w, gone = w.remove.includes(a.id);
  const effects = a.effects.map((e, i) => {
    const known = (c.effects[e.name] || []);
    const egone = w.remove.includes(e.id);
    const fields = e.fields.filter(f => f.tag !== 'name');
    const nm = e.fields.find(f => f.tag === 'name');
    return `<div class="cdbsec"${egone ? ' style="opacity:.45"' : ''}><h3>${nm ? `<select onchange="haxSet(${nm.id}, this.value, '${q1(esc(nm.value))}')">${
        [...new Set([haxVal(nm.id, nm.value), ...Object.keys(c.effects)])].map(o => `<option${o === haxVal(nm.id, nm.value) ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>` : '(no name)'}
      <span class="count">line ${e.line}</span> <button onclick="haxDrop(${e.id})">${egone ? 'keep' : 'Remove effect'}</button></h3>
      <table class="smxtab">${haxFieldRows(fields, ['target'])}${haxAddFieldHtml(e.id, fields.map(f => f.tag), known, 'e' + i)}</table></div>`;
  }).join('');
  const others = (c.abilities || []).flatMap(x => x.effects.map(e => ({id: e.id, label: `${x.name} · ${e.name}`})));
  const copies = w.copy.filter(x => x.into === a.effects_id).map(x =>
    `<div class="trnote">+ a copy of ${esc((others.find(o => o.id === x.like) || {}).label || '')}, on save</div>`).join('');
  const used = (a.used || []).map(u => `<div class="count"><code>${esc(u.file)}:${u.line}</code> ${esc(u.who)}</div>`).join('');
  return `<div class="cdbsec"><h3>${esc(a.name)} <span class="count">line ${a.line}</span>
      <button onclick="haxDrop(${a.id})">${gone ? 'Keep it' : 'Remove ability'}</button></h3>
    ${gone && a.used_count ? `<div class="trnote">⚠ ${a.used_count} character line(s) name it and will name nothing.</div>` : ''}
    <table class="smxtab">${haxFieldRows(a.fields, ['name'])}${haxAddFieldHtml(a.id, a.fields.map(f => f.tag), c.ability_fields || [], 'a')}</table>
    <div class="count">Duration and cooldown are seconds (a duration of 0 is instant); activations defaults to 1. The labels are
      <code>text/expanded.txt</code> keys, the sprites names in <code>ui/battle.sd</code>, the sound an <code>event</code> in
      <code>descr_sounds_generic.txt</code>.</div>
    <div class="trnote">Copy it as <input id="haxCopyName" style="width:200px" placeholder="New_Ability_Name">
      <button onclick="haxCopy(${a.id})">＋ Copy</button>
      ${w.copy.filter(x => x.like === a.id).map(x => `<span class="count">+ ${esc(x.name)} on save</span>`).join(' ')}</div>
  </div>
  <div class="cdbsec"><h3>Effects <span class="count">${a.effects.length}</span></h3></div>
  ${effects}
  ${copies}
  ${a.effects_id != null && others.length ? `<div class="trnote">Add an effect, a copy of
    <select id="haxLikeEffect">${others.map(o => `<option value="${o.id}">${esc(o.label)}</option>`).join('')}</select>
    <button onclick="haxAddEffect(${a.effects_id})">＋ Add</button></div>` : ''}
  <div class="cdbsec"><h3>Given to <span class="count">${a.used_count} line(s)</span></h3>
    ${used || '<div class="count">No character in any campaign or battle of this mod has it.</div>'}
    ${a.used_count > (a.used || []).length ? `<div class="count">…and ${a.used_count - a.used.length} more.</div>` : ''}</div>`;
}
function haxCopy(id){
  const name = (document.getElementById('haxCopyName').value || '').trim();
  if(!name) return toast('Name the copy first.');
  state.hax.w.copy.push({like: id, name});
  renderHeroAbilities();
}
function haxAddEffect(into){
  const like = +document.getElementById('haxLikeEffect').value;
  state.hax.w.copy.push({like, into});
  renderHeroAbilities();
}

async function haxSave(){
  const c = state.hax;
  if(c.busy) return;
  const body = Object.assign({mod: state.src, sig: c.sig || ''}, c.w);
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/heroabilities/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(`Write ${(p.changes || []).length} change(s)?\n\n` + (p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + '\n\nBacked up first, and 🕑 Log can undo it.')) return;
  let res;
  try{ res = await api.post('/api/heroabilities/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast('Saved. 🕑 Log can undo it.');
  await loadHeroAbilities();
}
