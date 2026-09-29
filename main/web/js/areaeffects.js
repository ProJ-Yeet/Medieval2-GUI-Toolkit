/* areaeffects.js - Area effects: descr_area_effects.xml

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ========================= AREA EFFECTS (67) =========================
   What a shot does where it lands. A projectile's `area_effect` line (and a
   holy cart's in descr_engines.txt) names one of these: a sickening cloud, a
   fire on the ground, an explosion, a shot that splits into more, a holy
   aura, or a set of them fired one after another. The one warning that
   matters is a projectile naming an area effect this file never declares.

   THE PAGE NEVER PARSES A GAME FILE: /api/areaeffects and its plan|apply. */

const AEX_TYPES = {
  nausea: tt('areaeffects.sickens_and_frightens_the_units_in'),
  holy: tt('areaeffects.lifts_the_morale_of_the_units'),
  fire: tt('areaeffects.burns_on_the_ground'),
  explosion: tt('areaeffects.throws_hurts_and_kills'),
  projectile: tt('areaeffects.splits_into_more_shots'),
  area_effect_set: tt('areaeffects.fires_other_area_effects_each_after'),
};

async function loadAreaEffects(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ` + esc(mod) + `${tt('areaeffects.s_area_effects')}</div>`;
  let r;
  try{ r = await api.get('/api/areaeffects?mod=' + enc(mod)); }
  catch(e){ if(stale('areaeffects', mod)) return;
    main.innerHTML = `<div class="empty">${tt('common.couldnt_read_them')}<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadAreaEffects()">${tt('common.retry')}</button></div>`; return; }
  if(stale('areaeffects', mod)) return;
  const keep = state.aex && state.aex.mod === mod ? state.aex : null;
  state.aex = Object.assign({mod, sel: keep ? keep.sel : '', w: aexBlank(), busy: false}, r);
  const list = r.effects || [];
  if(!list.some(e => String(e.id) === state.aex.sel))
    state.aex.sel = list.length ? String((list.find(e => e.used.length) || list[0]).id) : '';
  renderAreaEffects();
}
function aexBlank(){ return {values: {}, attrs: {}, remove: [], copy: [], add_field: []}; }
function aexChanged(){
  const w = state.aex.w;
  return Object.keys(w.values).length + Object.keys(w.attrs).length + w.remove.length
    + w.copy.length + w.add_field.length;
}

function renderAreaEffects(){
  const c = state.aex;
  if(!c){ loadAreaEffects(); return; }
  const strip = minorTabsHtml('', 'data/descr_area_effects.xml');
  const find = (c.findings || []).map(f => Object.assign({}, f, {name: f.key}));
  const n = aexChanged();
  const list = c.effects || [];
  const types = [...Object.keys(c.types || {}), ...new Set(list.map(e => e.type).filter(t => !(t in (c.types || {}))))];
  const left = c.error ? `<div class="count" style="padding:8px">${esc(c.error)}.</div>`
    : types.map(t => {
        const of = list.filter(e => e.type === t);
        if(!of.length) return '';
        return `<div class="trnote"><b>${esc(t || tt('areaeffects.no_type'))}</b> <span class="count">${esc(AEX_TYPES[t] || '')}</span></div>`
          + of.map(e => `<button class="trrow${c.sel === String(e.id) ? ' on' : ''}" onclick="aexPick('${e.id}')">
            <div class="nm">${esc(e.name || tt('common.no_name'))}${c.w.remove.includes(e.id) ? ` <span class="count">${tt('common.removed_on_save')}</span>` : ''}</div>
            <div class="sub">${aexUsedText(e)}${aexDirty(e) ? ` ${tt('common.changed')}` : ''}</div></button>`).join('');
      }).join('')
      + c.w.copy.filter(x => x.name).map(x => `<div class="trnote">${tt('areaeffects.on_save',{name:esc(x.name)})}</div>`).join('');
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('areaeffects', find, 'aexOpen')}
      <div class="trrows">${left}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div>${tt('areaeffects.descr_area_effects_xml_what_a')}</div>
        <span style="flex:1"></span>
        <button onclick="aexRevert()" ${n ? '' : 'disabled'}>${tt('common.revert')}</button>
        <button class="primary" onclick="aexSave()" ${n ? '' : 'disabled'}>${n ? ttN('areaeffects.save_changes_n',n) : tt('areaeffects.save_changes')}</button>
      </div>
      ${c.error ? '' : aexEffectHtml()}
    </div>
  </div>`;
}
function aexUsedText(e){
  const bits = [];
  if(e.used.length) bits.push(ttN('areaeffects.user_count',e.used.length));
  if(e.in_sets.length) bits.push(tt('areaeffects.in_set_s',{in_sets_n:e.in_sets.length}));
  if(e.members.length) bits.push(tt('areaeffects.member_s',{n:e.members.length}));
  return bits.join(' · ') || tt('areaeffects.named_by_nothing');
}

function aexEffect(){ const c = state.aex; return (c.effects || []).find(e => String(e.id) === c.sel); }
function aexDirty(e){
  const w = state.aex.w, ids = new Set([e.id, ...e.fields.map(f => f.id), ...e.members.map(m => m.id)]);
  return Object.keys(w.values).some(k => ids.has(+k)) || Object.keys(w.attrs).some(k => ids.has(+k))
    || w.remove.some(k => ids.has(k)) || w.copy.some(x => ids.has(x.like)) || w.add_field.some(x => ids.has(x.parent));
}
function aexPick(id){ state.aex.sel = String(id); renderAreaEffects(); }
function aexOpen(key){
  const [kind, rest] = String(key).split(/\/(.*)/);
  const c = state.aex, list = c.effects || [];
  if(kind === 'effect') c.sel = rest;
  else if(kind === 'name' || kind === 'use'){
    const e = list.find(x => x.name.toLowerCase() === String(rest).toLowerCase());
    if(e) c.sel = String(e.id);
    else if(kind === 'use') toast(tt('areaeffects.is_named_by_a_projectile_and',{rest}), 7000);
  }
  renderAreaEffects();
}
function aexRevert(){ state.aex.w = aexBlank(); renderAreaEffects(); }

function aexVal(id, v){ const w = state.aex.w.values; return w[id] !== undefined ? w[id] : v; }
function aexSet(id, v, was){
  const w = state.aex.w.values;
  if(v.trim() === was) delete w[id]; else w[id] = v.trim();
  renderAreaEffects();
}
function aexSetDelay(id, v, was){
  const w = state.aex.w.attrs;
  if(v.trim() === was) delete w[id]; else w[id] = {delay: v.trim()};
  renderAreaEffects();
}
function aexBox(f, width){
  const c = state.aex, v = aexVal(f.id, f.value), was = q1(esc(f.value));
  const pick = f.tag === 'type' ? Object.keys(c.types || {}) : f.tag === 'direction' ? c.directions
    : f.tag === 'preserve_momentum' ? ['true', 'false'] : null;
  if(pick){
    const opts = pick.includes(v) ? pick : [v, ...pick];
    return `<select onchange="aexSet(${f.id}, this.value, '${was}')">${opts.map(o =>
      `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
  }
  return `<input style="width:${width}px" value="${esc(v)}" onchange="aexSet(${f.id}, this.value, '${was}')">`;
}
function aexDrop(id){
  const r = state.aex.w.remove, i = r.indexOf(id);
  if(i >= 0) r.splice(i, 1); else r.push(id);
  renderAreaEffects();
}

function aexEffectHtml(){
  const c = state.aex, e = aexEffect();
  if(!e) return `<div class="count" style="padding:8px">${tt('areaeffects.pick_an_area_effect')}</div>`;
  const w = c.w, gone = w.remove.includes(e.id);
  const fixed = ['name', 'type', 'red', 'green', 'blue'];
  const rows = e.fields.map(f => {
    const fg = w.remove.includes(f.id);
    return `<tr${fg ? ' style="opacity:.45"' : ''}><td><code>${esc(f.path)}</code></td>
      <td>${aexBox(f, /effect$|projectile_type|^name$/.test(f.tag) ? 280 : 90)}</td>
      <td>${fixed.includes(f.tag) ? '' : `<button onclick="aexDrop(${f.id})">${fg ? 'keep' : '✕'}</button>`}</td></tr>`;
  }).join('');
  const known = ((c.types || {})[e.type] || []).filter(t => t !== 'banner_colour' && !(e.type === 'area_effect_set' && t === 'effect'));
  const have = e.fields.map(f => f.tag);
  const want = known.filter(t => !have.includes(t) && !w.add_field.some(x => x.parent === e.id && x.tag === t));
  const pending = w.add_field.filter(x => x.parent === e.id).map(x =>
    `<tr><td><code>${esc(x.tag)}</code></td><td>${tt('areaeffects.added_on_save',{value:esc(x.value)})}</td><td></td></tr>`).join('');
  const add = want.length ? `<tr><td><select id="aexAddTag">${want.map(t => `<option>${esc(t)}</option>`).join('')}</select></td>
    <td><input id="aexAddVal" style="width:200px" placeholder="${ttA('common.value')}"> <button onclick="aexAddField(${e.id})">${tt('common.add')}</button></td><td></td></tr>` : '';
  const names = (c.effects || []).map(x => x.name).filter(Boolean);
  const members = e.type === 'area_effect_set' ? `<div class="cdbsec"><h3>${tt('areaeffects.members_each_fired_after_its_delay',{members_n:e.members.length})}</h3>
    <table class="smxtab"><tr><th>${tt('areaeffects.area_effect')}</th><th>${tt('areaeffects.delay')}</th><th></th></tr>${e.members.map(m => {
      const mg = w.remove.includes(m.id), v = aexVal(m.id, m.name);
      const d = w.attrs[m.id] ? w.attrs[m.id].delay : m.delay;
      const opts = names.includes(v) ? names : [v, ...names];
      return `<tr${mg ? ' style="opacity:.45"' : ''}><td><select onchange="aexSet(${m.id}, this.value, '${q1(esc(m.name))}')">${
          opts.map(o => `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select></td>
        <td>${m.delay !== '' ? `<input style="width:60px" value="${esc(d)}" onchange="aexSetDelay(${m.id}, this.value, '${q1(esc(m.delay))}')">` : ''}</td>
        <td><button onclick="aexDrop(${m.id})">${mg ? tt('areaeffects.keep_member') : '✕'}</button></td></tr>`;
    }).join('')}
    ${w.copy.filter(x => e.members.some(m => m.id === x.like)).map(x =>
      `<tr><td colspan="3" class="count">${x.attrs ? tt('areaeffects.on_save_after_delay',{value:esc(x.value),delay:esc(x.attrs.delay)}) : tt('areaeffects.on_save_plain',{value:esc(x.value)})}</td></tr>`).join('')}
    </table>
    ${e.members.length ? `<div class="trnote">${tt('areaeffects.add_member_after_delay',{
        member:`<select id="aexMember">${names.map(o => `<option>${esc(o)}</option>`).join('')}</select>`,
        delay:`<input id="aexDelay" style="width:60px" value="${esc(e.members[e.members.length - 1].delay || '')}">`})}
      <button onclick="aexAddMember(${e.members[e.members.length - 1].id})">${tt('common.add')}</button></div>` : ''}</div>` : '';
  const used = e.used.map(u => `<div class="count"><code>${esc(u.file)}:${u.line}</code> ${esc(u.who)}</div>`).join('')
    + e.in_sets.map(s => `<div class="count">${tt('areaeffects.a_member_of_set',{set:`<a class="ulink" onclick="aexOpen('name/${q1(esc(s))}')">${esc(s)}</a>`})}</div>`).join('');
  return `<div class="cdbsec"><h3>${tt('areaeffects.line',{name:esc(e.name),type:esc(e.type),line:e.line})}
      <button onclick="aexDrop(${e.id})">${gone ? tt('common.keep_it') : tt('areaeffects.remove_area_effect')}</button></h3>
    ${gone && (e.used.length || e.in_sets.length) ? `<div class="trnote">${tt('areaeffects.thing_s_name_it_and_will',{n:e.used.length + e.in_sets.length})}</div>` : ''}
    <table class="smxtab">${rows}${pending}${add}</table>
    <div class="count">${e.type === 'area_effect_set' ? tt('areaeffects.a_set_fires_its_members')
      : tt('areaeffects.an_effect_ground_effect_or_floating')}
      ${(c.absent_effect_files || []).length ? tt('areaeffects.of_those_files_are_the_base',{absent_effect_files_n:c.absent_effect_files.length}) : ''}</div>
    <div class="trnote">${tt('areaeffects.copy_it_as')} <input id="aexCopyName" style="width:200px" placeholder="ae_new_name">
      <button onclick="aexCopy(${e.id})">${tt('common.copy')}</button>
      ${w.copy.filter(x => x.like === e.id).map(x => `<span class="count">${tt('areaeffects.on_save_3',{name:esc(x.name)})}</span>`).join(' ')}</div>
  </div>
  ${members}
  <div class="cdbsec"><h3>${tt('areaeffects.named_by')} <span class="count">${e.used.length + e.in_sets.length}</span></h3>
    ${used || `<div class="count">${tt('areaeffects.no_projectile_engine_or_set_in')}</div>`}</div>`;
}
function aexAddField(parent){
  const tag = document.getElementById('aexAddTag').value;
  const value = (document.getElementById('aexAddVal').value || '').trim();
  if(!value) return toast(tt('areaeffects.give_the_new_field_a_value'));
  state.aex.w.add_field.push({parent, tag, value});
  renderAreaEffects();
}
function aexAddMember(like){
  const value = document.getElementById('aexMember').value;
  const delay = (document.getElementById('aexDelay').value || '').trim();
  const spec = {like, value};
  if(delay) spec.attrs = {delay};
  state.aex.w.copy.push(spec);
  renderAreaEffects();
}
function aexCopy(id){
  const name = (document.getElementById('aexCopyName').value || '').trim();
  if(!name) return toast(tt('areaeffects.name_the_copy_first'));
  state.aex.w.copy.push({like: id, name});
  renderAreaEffects();
}

async function aexSave(){
  const c = state.aex;
  if(c.busy) return;
  const body = Object.assign({mod: state.src, sig: c.sig || ''}, c.w);
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/areaeffects/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(tt('areaeffects.write_confirm',{n:(p.changes || []).length,changes:(p.changes || []).slice(0, 16).join('\n'),
    warnings:(p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : ''}))) return;
  let res;
  try{ res = await api.post('/api/areaeffects/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  await loadAreaEffects();
}
