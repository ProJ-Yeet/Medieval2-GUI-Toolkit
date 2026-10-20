/* voices.js - hear a unit's voices by accent, and give it a name call of your
   own (96e5)

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   A panel over the Sounds list. The server finds each file the voice bank
   names, loose or in the game's SND.PACK archives, and hands its bytes to an
   <audio> element; nothing is unpacked. A name call of one's own is a .wav
   read here and sent once to plan (what would change, said first) and once to
   apply (backups and a log record, so the Log's Undo takes it back). From the
   Pfadfinder-Adam campaign editor, ported with its author's permission.
   Every name here starts `vx`.
   ===================================================================== */

function vxOpen(unit){
  const s = state.snd;
  s.hear = {unit, busy: true, accent: ''};
  renderSounds();
  vxLoad();
}

async function vxLoad(){
  const s = state.snd, h = s.hear;
  if(!h) return;
  let r;
  try{ r = await api.get(`/api/voices?mod=${enc(state.src)}&unit=${enc(h.unit)}&accent=${enc(h.accent || '')}`); }
  catch(e){ r = {error: errText(e)}; }
  if(state.snd !== s || s.hear !== h) return;
  Object.assign(h, {busy: false, r});
  if(!h.accent && r && !r.error) h.accent = r.heard || '';
  if(!h.ncAccent && r && !r.error){ h.ncAccent = r.heard || ''; h.ncClass = r.heard_class || ''; }
  renderSounds();
}

function vxClose(){ state.snd.hear = null; renderSounds(); }

function vxPlay(rel){
  const a = document.getElementById('vxAudio');
  if(!a) return;
  a.src = `/api/voices/play?mod=${enc(state.src)}&rel=${enc(rel)}`;
  a.play().catch(e => toast('✗ ' + errText(e), 4000));
}

function vxFilesHtml(files){
  return files.map(f => f.found
    ? `<button class="mini" title="${esc(f.rel)}" onclick="vxPlay('${q1(esc(f.rel))}')">▶ ${esc(f.rel.split('/').pop())}</button>`
    : `<span class="count w-warn" title="${ttA('voices.not_found_title')}">${esc(f.rel.split('/').pop())} ✗</span>`).join(' ');
}

function vxPanelHtml(){
  const h = (state.snd || {}).hear;
  if(!h) return '';
  const close = `<button class="mini" style="margin-left:auto" onclick="vxClose()">✕</button>`;
  if(h.busy && !h.r) return `<div class="bsec vxpanel"><h4>${esc(h.unit)} ${close}</h4><div class="count">${tt('common.reading')}</div></div>`;
  const r = h.r || {};
  if(r.error) return `<div class="bsec vxpanel"><h4>${esc(h.unit)} ${close}</h4><div class="w-bad">✗ ${esc(r.error)}</div></div>`;
  const opt = (v, cur) => `<option value="${esc(v)}" ${v === cur ? 'selected' : ''}>${esc(v)}</option>`;
  return `<div class="bsec vxpanel"><h4>${tt('voices.head',{unit:esc(h.unit)})} ${close}</h4>
    <audio id="vxAudio" preload="none"></audio>
    ${r.packs ? '' : `<div class="count w-warn">${tt('voices.no_packs')}</div>`}
    <div class="count">${tt('voices.edu_says',{accent:esc(r.accent || '-'), vclass:esc(r['class'] || '-')})}</div>
    <h5>${tt('voices.name_calls')}</h5>
    ${r.calls.length ? r.calls.map(c => `<div class="vxrow"><span class="vxlab">${esc(c.accent)} / ${esc(c['class'])}${
      c.shared ? ` <span class="count">${tt('voices.shared')}</span>` : ''}</span> ${vxFilesHtml(c.files)}</div>`).join('')
      : `<div class="count">${tt('voices.no_name_call')}</div>`}
    <h5>${tt('voices.orders')} <select onchange="state.snd.hear.accent=this.value;vxLoad()">
      ${r.accents.map(a => opt(a, h.accent)).join('')}</select></h5>
    ${r.orders.length ? r.orders.map(o => `<div class="vxrow"><span class="vxlab">${esc(o.vocal)}</span> ${vxFilesHtml(o.files)}</div>`).join('')
      : `<div class="count">${tt('voices.no_orders',{accent:esc(h.accent)})}</div>`}
    <h5>${tt('voices.own_head')}</h5>
    <div class="count">${tt('voices.own_note')}</div>
    <div class="vxrow">
      <select onchange="state.snd.hear.ncAccent=this.value">${r.accents.map(a => opt(a, h.ncAccent)).join('')}</select>
      <select onchange="state.snd.hear.ncClass=this.value">${r.classes.map(c => opt(c, h.ncClass)).join('')}</select>
      <input type="file" accept=".wav,audio/wav" multiple onchange="vxPickWavs(this.files)">
      <button class="primary" ${(h.wavs || []).length ? '' : 'disabled'} onclick="vxNameCall()">${tt('voices.own_go')}</button>
    </div>
    ${(h.wavs || []).length ? `<div class="count">${ttN('voices.wavs_picked', h.wavs.length)}</div>` : ''}
  </div>`;
}

async function vxPickWavs(files){
  const h = state.snd.hear;
  h.wavs = [];
  for(const f of files){
    const buf = new Uint8Array(await f.arrayBuffer());
    let bin = '';
    for(let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    h.wavs.push({name: f.name, b64: btoa(bin)});
  }
  renderSounds();
}

async function vxNameCall(){
  const h = state.snd.hear;
  const body = {mod: state.src, unit: h.unit, accent: h.ncAccent, 'class': h.ncClass, files: h.wavs};
  let p;
  try{ p = await api.post('/api/voices/namecall/plan', body); }catch(e){ toast('✗ ' + errText(e), 6000); return; }
  if(p.error){ toast('✗ ' + p.error, 8000); return; }
  if(!confirm(tt('voices.own_confirm',{changes:p.changes.join('\n'),
      warnings:p.warnings.length ? '\n\n⚠ ' + p.warnings.join('\n⚠ ') : '',
      compiled:p.compiled.length ? `\n\n${tt('voices.own_compiled')}` : ''}))) return;
  let r;
  try{ r = await api.post('/api/voices/namecall/apply', body); }catch(e){ toast('✗ ' + errText(e), 6000); return; }
  if(r.error){ toast('✗ ' + r.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  h.wavs = [];
  state.snd = null;
  await loadSounds();
  vxOpen(h.unit);
}
