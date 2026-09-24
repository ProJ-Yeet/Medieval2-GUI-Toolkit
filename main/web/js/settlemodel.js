/* settlemodel.js - Cultures: a settlement model brought in and put on a level

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   IMPORT A SETTLEMENT MODEL - Phase 74.

   Every name here starts `smi`. It opens under a culture's settlement ladder
   from the "Import…" beside each level's Model box, because that box is
   where the path it writes goes. The server does the rest: finds the
   textures the model names, picks a folder where nothing is written over,
   and splices the culture's line. One plan, one Undo.
   ===================================================================== */

function smiOpen(culture, target){
  state.smi = {culture, target, from: '', models: null, model: '', files: null,
               plan: null, busy: false, err: ''};
  mfPaintForm();
}

function smiClose(){
  state.smi = null;
  mfPaintForm();
}

async function smiFrom(src){
  const k = state.smi;
  if(!k) return;
  Object.assign(k, {from: src, models: null, model: '', files: null, plan: null, err: ''});
  mfPaintForm();
  if(!src || src === 'disk') return;
  try{
    const r = await api.get(`/api/settlemodel/models?mod=${enc(src)}`,
                            {label: `listing ${src}'s settlement models`});
    if(state.smi !== k || k.from !== src) return;
    k.models = r.models || [];
  }catch(e){
    if(state.smi !== k) return;
    k.err = errText(e);
  }
  mfPaintForm();
}

function smiModel(value){
  const k = state.smi;
  if(!k) return;
  k.model = value.trim();
  k.plan = null;
}

//: A model from disk: the .cas and whatever textures were picked with it,
//: read here and sent as they are. The server matches textures by name.
async function smiFiles(input){
  const k = state.smi;
  if(!k) return;
  const out = [];
  for(const f of input.files){
    const buf = new Uint8Array(await f.arrayBuffer());
    let bin = '';
    for(let i = 0; i < buf.length; i += 0x8000)
      bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    out.push({name: f.name, data: btoa(bin)});
  }
  if(state.smi !== k) return;
  k.files = out;
  k.plan = null;
  mfPaintForm();
}

function smiBody(){
  const k = state.smi;
  return {mod: state.src, from: k.from, model: k.model, files: k.files || [],
          culture: k.culture, target: k.target};
}

async function smiPlan(){
  const k = state.smi;
  if(!k || k.busy) return;
  k.busy = true; mfPaintForm();
  let res;
  try{ res = await api.post('/api/settlemodel/plan', smiBody(),
                            {label: 'working out the model'}); }
  catch(e){ res = {plan: {errors: [errText(e)]}}; }
  finally{ k.busy = false; }
  if(state.smi !== k) return;
  k.plan = res.plan || {errors: [res.error || 'the plan came back empty']};
  mfPaintForm();
}

async function smiApply(){
  const k = state.smi;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(`Put ${p.model} on ${k.culture} ${k.target}?\n\n`
    + (p.changes || []).join('\n')
    + ((p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')
    + '\n\nThe culture is read again from disk afterwards, so an edit to it that '
    + 'is not saved yet is dropped. 🕑 Log can undo it.')) return;
  k.busy = true; mfPaintForm();
  let res;
  try{ res = await api.post('/api/settlemodel/apply', smiBody(),
                            {label: `putting ${p.model} on ${k.target}`}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || 'the import failed'), 9000);
    mfPaintForm();
    return;
  }
  toast(`${k.culture} ${k.target} now draws ${res.rel}. 🕑 Log can undo it.`, 7000);
  activity('settlement model', `${state.src}: ${k.culture} ${k.target} -> ${res.rel}`);
  state.smi = null;
  await mfOpen(k.culture);
}

/* ---------- drawing, inside the culture form ---------- */

function smiButton(culture, target){
  return `<button class="trgadd" onclick="smiOpen('${q1(esc(culture))}','${q1(esc(target))}')"
    title="Bring a settlement model in from another mod or from disk, with the textures it names, and put it on this line.">Import…</button>`;
}

//: ``tail`` says which section asks: the ladder draws the picker for a level,
//: the fort section for one of its four model lines.
const SMI_TAIL = ['fort', 'fort_wall', 'fishing_village', 'watchtower'];
function smiHtml(culture, tail){
  const k = state.smi;
  if(!k || k.culture !== culture || SMI_TAIL.includes(k.target) !== !!tail) return '';
  const others = (state.mods || []).map(m => m.name).filter(n => n !== state.src);
  const p = k.plan;
  return `<div class="cbrrow" style="margin:8px 0">
    <div class="k">A model for ${esc(culture)} ${esc(k.target)}
      <span class="sp"></span><button class="trgadd" onclick="smiClose()">close</button></div>
    <div class="trgrid">
      <label class="lbl">From</label>
      <select onchange="smiFrom(this.value)">
        <option value="">pick…</option>
        ${others.map(n => `<option value="${esc(n)}"${n === k.from ? ' selected' : ''}
          >${esc(n)}</option>`).join('')}
        <option value="disk"${k.from === 'disk' ? ' selected' : ''}>a model on disk</option>
      </select>
      ${k.from === 'disk' ? `<label class="lbl">Files</label>
        <input type="file" multiple accept=".cas,.tga,.dds" onchange="smiFiles(this)">`
      : k.from ? `<label class="lbl">Model</label>
        <input list="smiList" value="${esc(k.model)}" placeholder="${k.models
          ? `${k.models.length} settlement models` : 'listing…'}"
          onchange="smiModel(this.value)">` : ''}
    </div>
    ${k.from === 'disk' ? `<div class="count">Pick the .cas and the textures it
      names together; they are matched by name.
      ${(k.files || []).length ? `${k.files.length} file(s) read.` : ''}</div>` : ''}
    ${k.models ? `<datalist id="smiList">${k.models.map(m =>
      `<option value="${esc(m.rel)}">`).join('')}</datalist>` : ''}
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    <div class="cmbar2">
      <button onclick="smiPlan()" ${k.busy || !k.from ? 'disabled' : ''}
        >${k.busy && !p ? 'working it out…' : 'Work it out'}</button>
    </div>
    ${p ? smiPlanHtml(k, p) : ''}
  </div>`;
}

function smiPlanHtml(k, p){
  if((p.errors || []).length) return `<div class="w-bad">${p.errors.map(esc).join('<br>')}</div>`;
  return `${(p.changes || []).map(x => `<div class="count">${esc(x)}</div>`).join('')}
    ${(p.textures || []).map(t => `<div class="count">${t.found ? '✓' : '✗'}
      ${esc(t.texture)}${t.found ? ` → ${esc(t.file)}` : ' - not found'}</div>`).join('')}
    ${(p.warnings || []).map(x => `<div class="w-warn">${esc(x)}</div>`).join('')}
    <div class="cmbar2">
      <button class="primary" onclick="smiApply()" ${k.busy ? 'disabled' : ''}
        >${k.busy ? 'writing…' : `Put it on ${esc(k.target)}`}</button>
      <span class="sp"></span><span class="count">🕑 Log can undo it.</span>
    </div>`;
}
