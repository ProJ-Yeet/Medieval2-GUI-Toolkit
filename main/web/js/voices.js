/* Unit voice listening and name-call uploads. Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor. */

function vxPaint(){ if(state.mode === 'sounds') renderSounds(); }
async function vxOpen(unit){
  if(!state.snd) return;
  const h = state.snd.hear = {unit, mod: state.src, files: [], busy: false};
  vxPaint();
  await vxRead(h, '');
}
async function vxRead(h, accent){
  const s = state.snd, token = h.request = {};
  h.loading = true; h.error = ''; vxPaint();
  let r;
  try{ r = await api.get(`/api/voices?mod=${enc(h.mod)}&unit=${enc(h.unit)}&accent=${enc(accent)}`); }
  catch(e){ r = {error: errText(e)}; }
  if(state.snd !== s || s.hear !== h || h.request !== token || state.src !== h.mod) return;
  h.loading = false; h.reply = r; h.error = r.error || '';
  h.listen = accent || r.heard || r.accent || '';
  if(h.accent === undefined){ h.accent = r.heard || ''; h.class = r.heard_class || ''; }
  vxPaint();
}
function vxClose(){ if(state.snd) state.snd.hear = null; vxPaint(); }
function vxOptions(list, value){
  const all = [...new Set([value, ...(list || [])].filter(Boolean))];
  return all.map(x => `<option value="${esc(x)}"${x === value ? ' selected' : ''}>${esc(x)}</option>`).join('');
}
function vxFilesHtml(files){
  return (files || []).map(f => f.found
    ? `<button class="mini" title="${esc(f.rel)}" onclick="vxPlay('${q1(esc(f.rel))}')">${esc(f.rel.split(/[\\/]/).pop())}</button>`
    : `<span class="w-warn" title="${ttA('voices.not_found_title')}">${esc(f.rel.split(/[\\/]/).pop())}</span>`).join(' ');
}
function vxPanelHtml(){
  const h = state.snd && state.snd.hear;
  if(!h) return '';
  let html = `<section class="bsec vxpanel"><h4>${tt('voices.head', {unit: esc(h.unit)})}<button class="mini" onclick="vxClose()">×</button></h4>`;
  if(h.loading || !h.reply) return html + `<div>${tt('common.reading')}</div></section>`;
  if(h.error) return html + `<div class="w-bad">${esc(h.error)}</div></section>`;
  const r = h.reply;
  return html + `${!r.packs ? `<p class="w-warn">${tt('voices.no_packs')}</p>` : ''}
    <p>${tt('voices.edu_says', {accent: esc(r.accent || '-'), vclass: esc(r.class || '-')})}</p>
    <h4>${tt('voices.name_calls')}</h4>
    ${(r.calls || []).map(c => `<div class="vxrow"><span class="vxlab">${esc(c.accent)} / ${esc(c.class)} ${c.shared ? tt('voices.shared') : ''}</span>${vxFilesHtml(c.files)}</div>`).join('') || `<p>${tt('voices.no_name_call')}</p>`}
    <h4>${tt('voices.orders')} <select onchange="vxRead(state.snd.hear,this.value)">${vxOptions(r.accents, h.listen)}</select></h4>
    ${(r.orders || []).map(o => `<div class="vxrow"><span class="vxlab">${esc(o.vocal)}</span>${vxFilesHtml(o.files)}</div>`).join('') || `<p>${h.listen ? tt('voices.no_orders', {accent: esc(h.listen)}) : tt('voices.no_orders_no_accent')}</p>`}
    <audio id="vxAudio" preload="none"></audio>
    <h4>${tt('voices.own_head')}</h4><p class="count">${tt('voices.own_note')}</p>
    <div class="vxrow"><select title="${esc(h.accent)}" onchange="state.snd.hear.accent=this.value">${vxOptions(r.accents, h.accent)}</select>
    <select title="${esc(h.class)}" onchange="state.snd.hear.class=this.value">${vxOptions(r.classes, h.class)}</select>
    <input type="file" accept=".wav,audio/wav" multiple onchange="vxPick(this.files)" ${h.busy ? 'disabled' : ''}>
    <span class="count">${ttN('voices.wavs_picked', h.files.length)}</span>
    <button class="primary" ${!h.files.length || h.reading || h.busy ? 'disabled' : ''} onclick="vxApply()">${tt('voices.own_go')}</button></div></section>`;
}
async function vxPlay(rel){
  const a = document.getElementById('vxAudio'), h = state.snd.hear;
  if(!a || !h) return;
  a.src = `/api/voices/play?mod=${enc(h.mod)}&rel=${enc(rel)}`;
  try{ await a.play(); }catch(e){ toast(errText(e)); }
}
async function vxPick(files){
  const s = state.snd, h = s.hear, token = h.pick = {};
  h.files = []; h.reading = true;
  const chosen = Array.from(files);
  vxPaint();
  try{
    const result = await Promise.all(chosen.map(f => new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve({name: f.name, b64: String(reader.result).split(',')[1]});
      reader.onerror = () => reject(reader.error); reader.readAsDataURL(f);
    })));
    if(state.snd === s && s.hear === h && h.pick === token) h.files = result;
  }catch(e){ toast(errText(e)); }
  if(state.snd === s && s.hear === h && h.pick === token){ h.reading = false; vxPaint(); }
}
async function vxApply(){
  const s = state.snd, h = s.hear;
  if(h.busy || h.reading || !h.files.length) return;
  const body = {mod: h.mod, unit: h.unit, accent: h.accent, class: h.class, files: h.files};
  h.busy = true; vxPaint();
  try{
    const p = await api.post('/api/voices/namecall/plan', body);
    if(p.error) throw new Error(p.error);
    if(state.snd !== s || s.hear !== h || state.src !== h.mod || state.mode !== 'sounds') return;
    if(!confirm(tt('voices.own_confirm', {changes: (p.changes || []).join('\n'), warnings: (p.warnings || []).join('\n'), compiled: (p.compiled || []).length ? `\n${tt('voices.own_compiled')}` : ''}))) return;
    const r = await api.post('/api/voices/namecall/apply', body);
    if(r.error) throw new Error(r.error);
    toast(tt('common.saved_log_can_undo_it')); h.files = [];
    if(state.snd === s && s.hear === h && state.src === h.mod && state.mode === 'sounds'){
      await loadSounds();
      if(state.src === h.mod && state.mode === 'sounds') await vxOpen(h.unit);
    }
  }catch(e){ toast(errText(e)); }
  finally{ h.busy = false; if(state.snd === s && s.hear === h) vxPaint(); }
}
