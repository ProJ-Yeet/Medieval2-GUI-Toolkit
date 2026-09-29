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
                            {label: tt('settlemodel.listing_s_settlement_models',{src})});
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
                            {label: tt('settlemodel.working_out_the_model')}); }
  catch(e){ res = {plan: {errors: [errText(e)]}}; }
  finally{ k.busy = false; }
  if(state.smi !== k) return;
  k.plan = res.plan || {errors: [res.error || tt('common.the_plan_came_back_empty')]};
  mfPaintForm();
}

async function smiApply(){
  const k = state.smi;
  if(!k || k.busy || !k.plan || !k.plan.ok) return;
  const p = k.plan;
  if(!confirm(tt('settlemodel.put_on_confirm',{model:p.model,culture:k.culture,target:k.target,
    changes:(p.changes || []).join('\n')
      + ((p.warnings || []).length ? '\n\n' + p.warnings.map(x => '⚠ ' + x).join('\n') : '')}))) return;
  k.busy = true; mfPaintForm();
  let res;
  try{ res = await api.post('/api/settlemodel/apply', smiBody(),
                            {label: tt('settlemodel.putting_on',{model:p.model,target:k.target})}); }
  catch(e){ res = {error: errText(e)}; }
  finally{ k.busy = false; }
  if(!res || res.error){
    toast('✗ ' + ((res && res.error) || tt('common.the_import_failed')), 9000);
    mfPaintForm();
    return;
  }
  toast(tt('settlemodel.now_draws_log_can_undo_it',{culture:k.culture,target:k.target,rel:res.rel}), 7000);
  activity(tt('settlemodel.settlement_model'), `${state.src}: ${k.culture} ${k.target} -> ${res.rel}`);
  state.smi = null;
  await mfOpen(k.culture);
}

/* ---------- drawing, inside the culture form ---------- */

function smiButton(culture, target){
  return `<button class="trgadd" onclick="smiOpen('${q1(esc(culture))}','${q1(esc(target))}')"
    title="${ttA('settlemodel.bring_a_settlement_model_in_from')}">${tt('settlemodel.import')}</button>`;
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
    <div class="k">${tt('settlemodel.a_model_for',{culture:esc(culture),target:esc(k.target)})}
      <span class="sp"></span><button class="trgadd" onclick="smiClose()">${tt('settlemodel.close')}</button></div>
    <div class="trgrid">
      <label class="lbl">${tt('common.from')}</label>
      <select onchange="smiFrom(this.value)">
        <option value="">${tt('settlemodel.pick')}</option>
        ${others.map(n => `<option value="${esc(n)}"${n === k.from ? ' selected' : ''}
          >${esc(n)}</option>`).join('')}
        <option value="disk"${k.from === 'disk' ? ' selected' : ''}>${tt('settlemodel.a_model_on_disk')}</option>
      </select>
      ${k.from === 'disk' ? `<label class="lbl">${tt('settlemodel.files')}</label>
        <input type="file" multiple accept=".cas,.tga,.dds" onchange="smiFiles(this)">`
      : k.from ? `<label class="lbl">${tt('settlemodel.model')}</label>
        <input list="smiList" value="${esc(k.model)}" placeholder="${k.models
          ? tt('settlemodel.settlement_models',{models_n:k.models.length}) : tt('settlemodel.listing')}"
          onchange="smiModel(this.value)">` : ''}
    </div>
    ${k.from === 'disk' ? `<div class="count">${tt('settlemodel.pick_the_cas_and_the_textures',{files:(k.files || []).length ? tt('settlemodel.file_s_read',{files_n:k.files.length}) : ''})}</div>` : ''}
    ${k.models ? `<datalist id="smiList">${k.models.map(m =>
      `<option value="${esc(m.rel)}">`).join('')}</datalist>` : ''}
    ${k.err ? `<div class="w-bad">${esc(k.err)}</div>` : ''}
    <div class="cmbar2">
      <button onclick="smiPlan()" ${k.busy || !k.from ? 'disabled' : ''}
        >${k.busy && !p ? tt('common.working_it_out') : tt('settlemodel.work_it_out')}</button>
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
        >${k.busy ? tt('common.writing') : tt('settlemodel.put_it_on',{target:esc(k.target)})}</button>
      <span class="sp"></span><span class="count">${tt('common.log_can_undo_it')}</span>
    </div>`;
}
