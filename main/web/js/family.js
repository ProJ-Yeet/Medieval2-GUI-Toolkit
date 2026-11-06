/* Editable campaign family tree and portraits. Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor. */

function fmBody(k){ return {mod: k.mod, campaign: k.d.campaign, faction: k.faction}; }
function fmSame(k, f){ return state.cx === k && k.fam === f; }
function fmReload(){ if(state.cx){ state.cx.fam = null; cxPaint(); } }
async function fmLoad(k, f){
  const query = Object.entries(fmBody(k)).map(([n,v]) => n + '=' + enc(v)).join('&');
  const read = async url => { try{ return await api.get(url + '?' + query); }catch(e){ return {error: errText(e)}; } };
  const results = await Promise.all([read('/api/family'), read('/api/portraits')]);
  if(!fmSame(k, f)) return;
  f.data = results[0]; f.library = results[1]; f.loading = false; cxPaint();
}
function fmView(f){
  const people = new Map((f.data.people || []).map(p => [p.name.toLowerCase(), {...p}]));
  const tree = new Map((f.data.tree || []).map(t => [t.father.toLowerCase(), {...t, children: [...(t.children || [])]}]));
  for(const op of f.ops){
    const key = (op.name || op.father).toLowerCase();
    if(op.op === 'record') people.set(key, {...op, source: 'record', fresh: true});
    if(op.op === 'drop_record') people.delete(key);
    if(op.op === 'family') tree.set(key, {...op, children: [...op.children], fresh: true});
    if(op.op === 'drop_family') tree.delete(key);
  }
  return {people, tree};
}
function fmPersonHtml(name, view, f){
  const key = name.toLowerCase(), p = view.people.get(key);
  const dead = p && (p.source === 'record' ? p.dead !== null && p.dead !== undefined && p.dead !== false : !!p.dead);
  return `<button class="fmbox${!p ? ' fmghost' : ''}${p && p.source === 'record' ? ' fmrec' : ''}${dead ? ' fmdead' : ''}${p && /^(female|f)$/i.test(p.sex) ? ' fmf' : ''}${p && p.fresh ? ' fmnew' : ''}${f.selected === key ? ' on' : ''}" onclick="fmSelect('${q1(esc(name))}')">
    ${esc(p ? p.name : name)}${p ? `<small>${p.source === 'map' ? tt('family.on_map_short') : tt('family.off_map_short')}</small>` : ''}${p && p.age != null ? `<small>${tt('family.age', {age: esc(p.age)})}</small>` : ''}
    ${p && /^(leader|heir)$/i.test(p.rank || '') ? `<span class="fmrank">${/^leader$/i.test(p.rank) ? tt('family.leader') : tt('family.heir')}</span>` : ''}</button>`;
}
function fmTreeHtml(view, f){
  const used = new Set(), drawn = new Set();
  const person = n => { used.add(n.toLowerCase()); return fmPersonHtml(n, view, f); };
  const branch = (t, ancestors) => {
    const key = t.father.toLowerCase();
    if(ancestors.has(key)) return person(t.father);
    drawn.add(key);
    const next = new Set(ancestors); next.add(key);
    return `<div class="fmfam${t.fresh ? ' fmnew' : ''}"><div class="fmcouple">${person(t.father)}${t.wife && t.wife.toLowerCase() !== 'nobody' ? `<span class="fmand">+</span>${person(t.wife)}` : ''}</div>
      <div class="fmkids">${t.children.map(n => `<div class="fmkid">${view.tree.has(n.toLowerCase()) ? branch(view.tree.get(n.toLowerCase()), next) : person(n)}</div>`).join('')}</div></div>`;
  };
  const childNames = new Set([...view.tree.values()].flatMap(t => t.children.map(n => n.toLowerCase())));
  let html = [...view.tree.values()].filter(t => !childNames.has(t.father.toLowerCase())).map(t => branch(t, new Set())).join('');
  for(const [key,t] of view.tree) if(!drawn.has(key)) html += branch(t, new Set());
  const loose = [...view.people.values()].filter(p => !used.has(p.name.toLowerCase()));
  return `<div class="fmtree">${html || `<p>${tt('family.no_lines')}</p>`}</div>${loose.length ? `<div class="fmloose"><h4>${tt('family.not_in_tree')}</h4>${loose.map(p => person(p.name)).join('')}</div>` : ''}`;
}
function fmHtml(){
  const k = state.cx;
  if(!k.fam){ k.fam = {loading: true, ops: [], selected: '', form: {name: '', age: 20, dead: false, sex: 'male'}}; fmLoad(k, k.fam); }
  const f = k.fam;
  if(f.loading) return `<div>${tt('common.reading')}</div>`;
  if(f.data.error) return `<div class="w-bad">${esc(f.data.error)}</div>`;
  const view = fmView(f);
  return `<div class="fmwrap"><div class="fmmain">${fmTreeHtml(view, f)}
    ${(f.data.findings || []).map(x => `<p class="w-warn">${esc(x.message)}</p>`).join('')}${fmLibraryHtml(f.library)}</div>
    <aside class="fmside">${fmSelectedHtml(view, f)}${fmOpsHtml(f)}</aside></div>`;
}
function fmSelect(name){
  const f = state.cx.fam, key = name.toLowerCase();
  f.selected = f.selected === key ? '' : key;
  f.form = {name: '', age: 20, dead: false, sex: 'male'}; cxPaint();
}
function fmSurname(surname){
  const f = state.cx.fam, pool = cxPoolOf();
  if(pool) f.form.name = cxWithSurname(f.form.name, surname, pool);
  cxPaint();
}
function fmSelectedHtml(view, f){
  const p = view.people.get(f.selected);
  if(!p) return `<div class="fmpanel">${tt('family.pick_someone')}</div>`;
  const male = !/^(female|f)$/i.test(p.sex), w = f.form;
  const action = (what, key) => `<button onclick="fmRelative('${what}')">${tt(key)}</button>`;
  return `<div class="fmpanel"><h4>${esc(p.name)}</h4><p class="count">${p.source === 'map' ? tt('family.on_map') : tt('family.off_map')}</p>
    <div class="fmform"><input list="fml-first" value="${esc(w.name)}" placeholder="${ttA('family.new_name')}" oninput="state.cx.fam.form.name=this.value">
    ${cxNamePickHtml('fml-first', '', w.name, 'fmSurname')}
    <input type="number" min="0" max="120" title="${ttA('family.age_title')}" value="${esc(w.age)}" oninput="state.cx.fam.form.age=this.value">
    <label class="chk"><input type="checkbox" ${w.dead ? 'checked' : ''} onchange="state.cx.fam.form.dead=this.checked">${tt('family.dead')}</label></div>
    <div class="fmacts">${male ? action('son','family.add_son') + action('daughter','family.add_daughter') + action('wife','family.add_wife') : ''}
    ${action('father','family.add_father')}<select onchange="state.cx.fam.form.sex=this.value"><option value="male"${w.sex === 'male' ? ' selected' : ''}>${tt('family.brother')}</option><option value="female"${w.sex === 'female' ? ' selected' : ''}>${tt('family.sister')}</option></select>${action('sibling','family.add_sibling')}
    ${male && view.tree.has(f.selected) ? action('drop_family','family.drop_line') : ''}${p.source === 'record' ? action('drop_record','family.drop_record') : ''}</div>
    ${p.source === 'map' ? `<div class="fmport"><p>${p.portrait ? tt('family.portrait_has',{folder: esc(p.portrait)}) : tt('family.portrait_none')}</p><label class="btn">${tt('family.portrait')}<input type="file" accept="image/*,.tga" onchange="fmPortrait(this.files[0])"></label></div>` : ''}</div>`;
}
function fmRelative(action){
  const f = state.cx.fam, v = fmView(f), p = v.people.get(f.selected);
  if(!p) return;
  if(action === 'drop_record') f.ops.push({op: action, name: p.name});
  else if(action === 'drop_family') f.ops.push({op: action, father: p.name});
  else{
    const name = f.form.name.trim();
    if(!name){ toast(tt('family.need_name')); return; }
    let line = v.tree.get(f.selected) || {father: p.name, wife: 'nobody', children: []};
    if(action === 'sibling'){
      line = [...v.tree.values()].find(t => t.children.some(n => n.toLowerCase() === f.selected));
      if(!line){ toast(tt('family.no_parents')); return; }
    }
    const sex = action === 'wife' || action === 'daughter' ? 'female' : action === 'sibling' ? f.form.sex : 'male';
    f.ops.push({op: 'record', name, sex, age: Number(f.form.age) || 20, dead: !!f.form.dead});
    if(action === 'father') f.ops.push({op: 'family', father: name, wife: 'nobody', children: [p.name]});
    else f.ops.push({op: 'family', father: line.father, wife: action === 'wife' ? name : line.wife,
      children: action === 'wife' ? [...line.children] : [...line.children, name]});
    f.form.name = '';
  }
  f.plan = null; cxPaint();
}
function fmOpsHtml(f){
  if(!f.ops.length) return '';
  const p = f.plan;
  return `<div class="fmops"><h4>${ttN('family.staged', f.ops.length)}</h4>
    <button onclick="state.cx.fam.ops=[];state.cx.fam.plan=null;cxPaint()">${tt('common.revert')}</button>
    <button ${f.busy ? 'disabled' : ''} onclick="fmWrite(false)">${tt('family.check')}</button>
    ${p ? (p.errors || []).map(x => `<p class="w-bad">${esc(x)}</p>`).join('') + (p.changes || []).map(x => `<p>${esc(x)}</p>`).join('') + (p.warnings || []).map(x => `<p class="w-warn">${esc(x)}</p>`).join('') : ''}
    ${p && p.ok ? `<button class="primary" ${f.busy ? 'disabled' : ''} onclick="fmWrite(true)">${tt('family.write')}</button>` : ''}</div>`;
}
async function fmWrite(apply){
  const k = state.cx, f = k.fam;
  if(f.busy || (apply && !(f.plan && f.plan.ok))) return;
  const ops = JSON.parse(JSON.stringify(f.ops));
  f.busy = true; cxPaint();
  try{
    const r = await api.post('/api/family/' + (apply ? 'apply' : 'plan'), {...fmBody(k), ops});
    if(r.error) throw new Error(r.error);
    if(!fmSame(k,f)) return;
    if(apply){ toast(tt('common.saved_log_can_undo_it')); fmReload(); }
    else if(JSON.stringify(f.ops) === JSON.stringify(ops)) f.plan = r;
  }catch(e){ toast(errText(e)); }
  finally{ f.busy = false; if(fmSame(k,f)) cxPaint(); }
}
function fmReadImage(file){
  return new Promise((resolve,reject) => { const r = new FileReader(); r.onload = () => resolve(String(r.result).split(',')[1]); r.onerror = () => reject(r.error); r.readAsDataURL(file); });
}
async function fmPortrait(file){
  if(!file) return;
  const k = state.cx, f = k.fam, p = fmView(f).people.get(f.selected);
  if(!p || p.source !== 'map') return;
  try{
    const b64 = await fmReadImage(file);
    if(!fmSame(k,f)) return;
    const r = await api.post('/api/family/portrait', {...fmBody(k), name: p.name, b64});
    if(r.error) throw new Error(r.error);
    toast(tt('common.saved_log_can_undo_it')); if(fmSame(k,f)) fmReload();
  }catch(e){ toast(errText(e)); }
}
function fmLibraryHtml(lib){
  if(!lib || lib.error) return '';
  return `<div class="fmlib"><h4>${tt('family.library',{culture: esc(lib.culture)})}</h4>
    <p class="count">${tt('family.library_note',{w: lib.size[0], h: lib.size[1]})}</p>
    ${Object.entries(lib.groups || {}).map(([group, counts]) => `<div class="fmlibrow"><b>${esc(group)}</b> ${Object.entries(counts).map(([age,n]) => `${esc(age)}: ${esc(n)}`).join(' · ')}
      <label class="btn">${tt('family.library_add')}<input type="file" accept="image/*,.tga" multiple onchange="fmLibraryAdd('${q1(esc(group))}',this.files)"></label></div>`).join('')}</div>`;
}
async function fmLibraryAdd(group, files){
  const chosen = Array.from(files); if(!chosen.length) return;
  const k = state.cx, f = k.fam, culture = f.library.culture;
  try{
    const data = await Promise.all(chosen.map(fmReadImage)); if(!fmSame(k,f)) return;
    const r = await api.post('/api/portraits/add', {mod: k.mod, culture, group, files: data});
    if(r.error) throw new Error(r.error);
    toast(tt('family.library_added',{n: chosen.length, group})); if(fmSame(k,f)) fmReload();
  }catch(e){ toast(errText(e)); }
}
