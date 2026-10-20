/* family.js - the faction's family tree drawn and edited; portraits (96e3)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   The Family tab of the characters panel. descr_strat.txt holds one
   `relative` line per father - his wife, then his children - and the game
   draws its tree from those lines alone; this draws the same tree: a couple
   side by side, their children below, the leader and the heir marked, a
   person off the map (a character_record) dashed, the dead greyed.

   Every change is an operation on the server's stratfamily module - set a
   father's line, add a person off the map, take either out - staged here,
   planned (the sentences shown) and written as one job the Log can undo.
   A son, a daughter, a father or a sibling is a person off the map plus the
   line that ties him in, so each is two operations. From the Pfadfinder-Adam
   campaign editor's family tree, ported with its author's permission.
   Every name here starts `fm`.
   ===================================================================== */

async function fmLoad(){
  const k = state.cx;
  if(!k || !k.d) return;
  k.fam = {busy: true, ops: [], pick: ''};
  cxPaint();
  let r, lib;
  const q = `mod=${enc(k.mod)}&campaign=${enc(k.d.campaign || '')}&faction=${enc(k.faction)}`;
  try{ r = await api.get('/api/family?' + q); }catch(e){ r = {error: errText(e)}; }
  try{ lib = await api.get('/api/portraits?' + q); }catch(e){ lib = {error: errText(e)}; }
  if(state.cx !== k) return;
  k.fam = Object.assign({ops: [], pick: '', lib}, r);
  cxPaint();
}

function fmPerson(name){
  const f = state.cx.fam;
  return (f.people || []).find(p => p.name.toLowerCase() === String(name).toLowerCase());
}

/* the tree as it will be after the staged operations, so the drawing shows them */
function fmStaged(){
  const f = state.cx.fam;
  const people = (f.people || []).slice(), tree = (f.tree || []).map(t => Object.assign({}, t));
  for(const op of f.ops){
    if(op.op === 'record') people.push({name: op.name, source: 'record', sex: op.sex, age: op.age, dead: op.dead ? 0 : null, staged: true});
    else if(op.op === 'drop_record') { const i = people.findIndex(p => p.name === op.name); if(i >= 0) people.splice(i, 1); }
    else if(op.op === 'family'){
      const i = tree.findIndex(t => t.father.toLowerCase() === op.father.toLowerCase());
      const row = {father: op.father, wife: op.wife || 'nobody', children: op.children.slice(), staged: true};
      if(i >= 0) tree[i] = row; else tree.push(row);
    }else if(op.op === 'drop_family'){
      const i = tree.findIndex(t => t.father.toLowerCase() === op.father.toLowerCase());
      if(i >= 0) tree.splice(i, 1);
    }
  }
  return {people, tree};
}

function fmBox(name, people){
  const p = people.find(x => x.name.toLowerCase() === String(name).toLowerCase());
  const f = state.cx.fam;
  if(!p) return `<span class="fmbox fmghost">${esc(name)}</span>`;
  const dead = p.source === 'record' && p.dead !== null && p.dead !== undefined;
  const mark = p.rank === 'leader' ? `<span class="fmrank">${tt('family.leader')}</span>`
    : p.rank === 'heir' ? `<span class="fmrank">${tt('family.heir')}</span>` : '';
  return `<button class="fmbox${p.source === 'record' ? ' fmrec' : ''}${dead ? ' fmdead' : ''}${p.sex === 'female' ? ' fmf' : ''}${
      f.pick === p.name ? ' on' : ''}${p.staged ? ' fmnew' : ''}" onclick="fmPick('${q1(esc(p.name))}')"
    title="${ttA(p.source === 'record' ? 'family.off_map' : 'family.on_map')}">
    <b>${esc(p.name)}</b>${mark}<span class="count">${p.age !== undefined && p.age !== null ? tt('family.age',{age:p.age}) : ''}</span></button>`;
}

function fmFamilyHtml(fam, byFather, people, seen){
  if(seen.has(fam.father.toLowerCase())) return '';
  seen.add(fam.father.toLowerCase());
  const kids = fam.children.map(c => {
    const own = byFather[c.toLowerCase()];
    return `<div class="fmkid">${own ? fmFamilyHtml(own, byFather, people, seen) : fmBox(c, people)}</div>`;
  }).join('');
  return `<div class="fmfam${fam.staged ? ' fmnew' : ''}"><div class="fmcouple">${fmBox(fam.father, people)}${
      fam.wife && fam.wife.toLowerCase() !== 'nobody' ? `<span class="fmand">&amp;</span>${fmBox(fam.wife, people)}` : ''}</div>
    ${kids ? `<div class="fmkids">${kids}</div>` : ''}</div>`;
}

function fmTreeHtml(){
  const {people, tree} = fmStaged();
  const byFather = {}, child = new Set(), inTree = new Set();
  tree.forEach(t => { byFather[t.father.toLowerCase()] = t; inTree.add(t.father.toLowerCase());
    if(t.wife) inTree.add(t.wife.toLowerCase()); t.children.forEach(c => { child.add(c.toLowerCase()); inTree.add(c.toLowerCase()); }); });
  const roots = tree.filter(t => !child.has(t.father.toLowerCase()));
  const seen = new Set();
  const loose = people.filter(p => !inTree.has(p.name.toLowerCase()));
  return `<div class="fmtree">${roots.map(r => fmFamilyHtml(r, byFather, people, seen)).join('') ||
      `<div class="count">${tt('family.no_lines')}</div>`}</div>
    ${loose.length ? `<div class="k">${tt('family.not_in_tree')}</div><div class="fmloose">${loose.map(p => fmBox(p.name, people)).join('')}</div>` : ''}`;
}

function fmPick(name){ state.cx.fam.pick = state.cx.fam.pick === name ? '' : name; state.cx.fam.form = null; cxPaint(); }

function fmStage(...ops){
  const f = state.cx.fam;
  f.ops.push(...ops);
  f.plan = null;
  cxPaint();
}

function fmLineOf(name){
  const {tree} = fmStaged();
  return tree.find(t => t.father.toLowerCase() === name.toLowerCase());
}
function fmParentsOf(name){
  const {tree} = fmStaged();
  return tree.find(t => t.children.some(c => c.toLowerCase() === name.toLowerCase()));
}

/* a person off the map, and the line that ties him in */
function fmAdd(kind){
  const f = state.cx.fam, P = f.pick, form = f.form || {};
  const name = (form.name || '').trim();
  if(!name){ toast(tt('family.need_name'), 4000); return; }
  const age = +form.age || 20, dead = !!form.dead;
  const sex = kind === 'daughter' || kind === 'wife' ? 'female' : kind === 'sibling' ? (form.sex || 'male') : 'male';
  const rec = {op: 'record', name, sex, age, dead};
  if(kind === 'son' || kind === 'daughter'){
    const line = fmLineOf(P) || {father: P, wife: 'nobody', children: []};
    fmStage(rec, {op: 'family', father: P, wife: line.wife, children: line.children.concat([name])});
  }else if(kind === 'wife'){
    const line = fmLineOf(P) || {father: P, wife: 'nobody', children: []};
    fmStage(rec, {op: 'family', father: P, wife: name, children: line.children});
  }else if(kind === 'father'){
    fmStage(rec, {op: 'family', father: name, wife: 'nobody', children: [P]});
  }else if(kind === 'sibling'){
    const par = fmParentsOf(P);
    if(!par){ toast(tt('family.no_parents'), 5000); return; }
    fmStage(rec, {op: 'family', father: par.father, wife: par.wife, children: par.children.concat([name])});
  }
  f.form = null;
}

function fmPanelHtml(){
  const f = state.cx.fam, P = f.pick && fmPerson(f.pick) || (fmStaged().people.find(p => p.name === f.pick));
  if(!P) return `<div class="count">${tt('family.pick_someone')}</div>`;
  const form = f.form || (f.form = {name: '', age: 20, sex: 'male', dead: false});
  const male = P.sex !== 'female';
  const btn = (k, label) => `<button onclick="fmAdd('${k}')">${label}</button>`;
  return `<div class="fmpanel"><div class="k">${esc(P.name)} · ${P.source === 'record' ? tt('family.off_map_short') : tt('family.on_map_short')}</div>
    <div class="fmform">
      <input placeholder="${ttA('family.new_name')}" value="${esc(form.name)}" oninput="state.cx.fam.form.name=this.value">
      <input type="number" min="0" max="120" value="${esc(form.age)}" title="${ttA('family.age_title')}" oninput="state.cx.fam.form.age=this.value" style="width:64px">
      <label class="chk"><input type="checkbox" ${form.dead ? 'checked' : ''} onchange="state.cx.fam.form.dead=this.checked"> ${tt('family.dead')}</label>
    </div>
    <div class="fmacts">
      ${male ? btn('son', tt('family.add_son')) + btn('daughter', tt('family.add_daughter')) + btn('wife', tt('family.add_wife')) : ''}
      ${btn('father', tt('family.add_father'))}
      <select onchange="state.cx.fam.form.sex=this.value"><option value="male">${tt('family.brother')}</option><option value="female" ${form.sex === 'female' ? 'selected' : ''}>${tt('family.sister')}</option></select>${btn('sibling', tt('family.add_sibling'))}
    </div>
    ${male && fmLineOf(P.name) ? `<button onclick="fmStage({op:'drop_family',father:'${q1(esc(P.name))}'})">${tt('family.drop_line')}</button>` : ''}
    ${P.source === 'record' ? `<button class="danger" onclick="fmStage({op:'drop_record',name:'${q1(esc(P.name))}'})">${tt('family.drop_record')}</button>` : ''}
    ${P.source === 'map' ? `<div class="fmport"><label class="btn">${tt('family.portrait')}
        <input type="file" accept="image/*,.tga" style="display:none" onchange="fmPortrait(this.files[0])"></label>
      <span class="count">${P.portrait ? tt('family.portrait_has',{folder:esc(P.portrait)}) : tt('family.portrait_none')}</span></div>` : ''}
  </div>`;
}

async function fmFileB64(file){
  const buf = new Uint8Array(await file.arrayBuffer());
  let bin = '';
  for(let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
  return btoa(bin);
}

async function fmPortrait(file){
  const k = state.cx, f = k.fam;
  if(!file) return;
  let r;
  try{ r = await api.post('/api/family/portrait', {mod: k.mod, campaign: k.d.campaign, faction: k.faction,
    name: f.pick, b64: await fmFileB64(file)}); }catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  fmLoad();
}

async function fmPlan(){
  const k = state.cx, f = k.fam;
  let r;
  try{ r = await api.post('/api/family/plan', {mod: k.mod, campaign: k.d.campaign, faction: k.faction, ops: f.ops}); }
  catch(e){ r = {error: errText(e)}; }
  f.plan = r;
  cxPaint();
}

async function fmApply(){
  const k = state.cx, f = k.fam;
  let r;
  try{ r = await api.post('/api/family/apply', {mod: k.mod, campaign: k.d.campaign, faction: k.faction, ops: f.ops}); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  fmLoad();
}

function fmLibHtml(){
  const lib = state.cx.fam.lib;
  if(!lib || lib.error || !lib.culture) return '';
  const groups = Object.entries(lib.groups || {});
  return `<div class="k">${tt('family.library',{culture:esc(lib.culture)})}</div>
    <div class="count">${tt('family.library_note',{w:lib.size[0], h:lib.size[1]})}</div>
    <div class="fmlib">${groups.map(([g, ages]) => `<div class="fmlibrow"><b>${esc(g)}</b>
      <span class="count">${Object.entries(ages).map(([a, n]) => `${esc(a)} ${n}`).join(' · ')}</span>
      <label class="btn">${tt('family.library_add')}<input type="file" accept="image/*,.tga" multiple style="display:none"
        onchange="fmLibAdd('${q1(esc(g))}', this.files)"></label></div>`).join('')}</div>`;
}

async function fmLibAdd(group, files){
  const k = state.cx, lib = k.fam.lib;
  if(!files || !files.length) return;
  const b64 = [];
  for(const f of files) b64.push(await fmFileB64(f));
  let r;
  try{ r = await api.post('/api/portraits/add', {mod: k.mod, culture: lib.culture, group, files: b64}); }
  catch(e){ r = {error: errText(e)}; }
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  toast(tt('family.library_added',{n:b64.length, group}));
  fmLoad();
}

function fmHtml(){
  const k = state.cx, f = k.fam;
  if(!f){ setTimeout(fmLoad, 0); return `<div class="count">${tt('common.reading')}</div>`; }
  if(f.busy) return `<div class="count">${tt('common.reading')}</div>`;
  if(f.error) return `<div class="w-bad">✗ ${esc(f.error)}</div>`;
  const p = f.plan;
  return `<div class="fmwrap">
    <div class="fmmain">${fmTreeHtml()}</div>
    <div class="fmside">${fmPanelHtml()}
      ${f.ops.length ? `<div class="fmops"><div class="k">${ttN('family.staged', f.ops.length)}</div>
        <button onclick="state.cx.fam.ops=[];state.cx.fam.plan=null;cxPaint()">${tt('common.revert')}</button>
        <button onclick="fmPlan()">${tt('family.check')}</button>
        ${p ? `${(p.errors || []).map(e => `<div class="w-bad">✗ ${esc(e)}</div>`).join('')}
          ${(p.changes || []).map(c => `<div class="count">${esc(c)}</div>`).join('')}
          ${(p.warnings || []).map(w => `<div class="w-warn">${esc(w)}</div>`).join('')}
          ${p.ok ? `<button class="primary" onclick="fmApply()">${tt('family.write')}</button>` : ''}` : ''}</div>` : ''}
      ${(f.findings || []).map(x => `<div class="w-warn">${esc(x.message)}</div>`).join('')}
    </div></div>
    ${fmLibHtml()}`;
}
