const HX_TAB_KEYS = {checks:'healthx.tab_checks',log:'healthx.tab_log',report:'healthx.tab_report',deep:'healthx.tab_deep'};
const HX_REPORT_KEYS = {c_factions:'healthx.c_factions',c_cultures:'healthx.c_cultures',c_religions:'healthx.c_religions',c_units:'healthx.c_units',c_chains:'healthx.c_chains',c_regions:'healthx.c_regions',c_towns:'healthx.c_towns',c_characters:'healthx.c_characters',c_faction:'healthx.c_faction',c_culture:'healthx.c_culture',c_religion:'healthx.c_religion',c_status:'healthx.c_status',c_armies:'healthx.c_armies',by_category:'healthx.by_category',by_class:'healthx.by_class',by_owner:'healthx.by_owner'};
/* Health game log, contents and rehearsal panels. Written independently from a description of the behaviour (2026-11-06); the feature follows Pfadfinder-Adam's campaign editor. */

function hxTabsHtml(){
  const tab = state.hl.tab || 'checks';
  return `<div class="hxtabs">${['checks','log','report','deep'].map(t => `<button class="${t === tab ? 'on' : ''}" onclick="hxSelect('${t}')">${tt(HX_TAB_KEYS[t])}</button>`).join('')}</div>`;
}
function hxSelect(tab){ state.hl.tab = tab; hlPaint(); }
async function hxLoad(part, refresh){
  const h = state.hl;
  if(h[part] && !refresh) return;
  const slot = h[part] = {loading:true, owner:h};
  const route = {log:'/api/gamelog',report:'/api/modreport',sets:'/api/rehearse/sets'}[part];
  let r;
  try{ r = await api.get(route + '?mod=' + enc(h.mod)); }catch(e){ r = {error:errText(e)}; }
  if(state.hl !== h || h[part] !== slot) return;
  h[part] = r; if(state.mode === 'health' && state.src === h.mod) hlPaint();
}
function hxPanelHtml(){
  const h = state.hl, tab = h.tab || 'checks';
  if(tab === 'checks') return '';
  const part = tab === 'deep' ? 'sets' : tab;
  if(!h[part] || h[part].loading && h[part].owner !== h) hxLoad(part,true);
  const r = h[part];
  if(!r || r.loading) return `<div class="empty">${tt('healthx.reading')}</div>`;
  if(r.error) return `<section class="bsec w-bad">${esc(r.error)} <button onclick="hxLoad('${part}',true)">${tt('health.run_again')}</button></section>`;
  return tab === 'log' ? hxLogHtml(r) : tab === 'report' ? hxReportHtml(r) : hxDeepHtml(r);
}
function hxAge(seconds){
  if(seconds >= 86400) return ttN('healthx.days_ago',Math.floor(seconds/86400));
  if(seconds >= 3600) return ttN('healthx.hours_ago',Math.floor(seconds/3600));
  if(seconds >= 60) return ttN('healthx.minutes_ago',Math.floor(seconds/60));
  return tt('healthx.just_now');
}
function hxFold(label, text){ return `<details class="hxraw"><summary>${label}</summary><pre class="hxpre">${esc(text)}</pre></details>`; }
function hxNow(text){ return text ? `<div class="hxnow"><span class="count">${tt('healthx.reads_now')}</span><pre class="hxpre">${esc(text)}</pre></div>` : ''; }
function hxFixHtml(fix,file,line){
  if(!fix) return '';
  const kind = fix.kind, name = fix.name || file || '';
  if(!['unit','building','file'].includes(kind)) return '';
  const label = kind === 'unit' ? tt('healthx.fix_unit',{name:esc(name)}) : kind === 'building' ? tt('healthx.fix_building',{name:esc(name)}) : tt('healthx.fix_file',{file:esc(name)});
  return `<button class="mini" onclick="hxFix('${kind}','${q1(esc(name))}',${Number(line) || 1})">${label}</button>`;
}
async function hxFix(kind,name,line){
  const mod = state.hl.mod;
  if(kind === 'building'){ window.open('/?mod=' + enc(mod) + '&building=' + enc(name),'_blank','noopener'); return; }
  if(kind === 'file'){
    let path = name.replace(/\\/g,'/');
    const m = /(?:^|\/)data\//i.exec(path); if(m) path = path.slice(m.index + m[0].length);
    rtOpen(path,line); return;
  }
  state.src = mod; setAppMode('edit');
  await loadSource();
  if(state.src !== mod || state.mode !== 'edit') return;
  const units = state.data && state.data.units || [];
  const found = units.find(u => u.type === name);
  if(found) openEditor(found.type);
  else toast(tt('core.is_not_a_unit_in',{qEdit:name,src:mod}));
}
function hxLogHtml(r){
  const reload = `<button class="mini" onclick="hxLoad('log',true)">${tt('health.run_again')}</button>`;
  if(!r.found) return `<section class="bsec"><h4>${tt('healthx.no_log')} ${reload}</h4><p style="white-space:pre-wrap">${esc(r.howto || '')}</p>${hxFold(tt('healthx.looked_in'),(r.looked || []).join('\n'))}</section>`;
  const v = r.verdict || {}, groups = r.groups || [];
  const problems = groups.filter(g => g.level !== 'warning' && g.level !== 'warn' && !(v.stopped && g.level === 'fatal' && /unspecified error/i.test(g.msg || '')));
  const notes = groups.filter(g => g.level === 'warning' || g.level === 'warn');
  let location = '';
  if(v.file && v.line) location = tt('healthx.crash_after_line',{file:esc(v.file),line:v.line,col:v.col ? tt('healthx.at_col',{col:v.col}) : ''});
  const problemCount = groups.length + (r.more || 0);
  return `<section class="bsec"><div class="hxloghead" title="${esc(r.path)}">${tt('healthx.read_from',{age:esc(hxAge(r.age))})} ${r.cut ? `<span class="count">${tt('healthx.log_cut')}</span>` : ''}
    <button class="mini" title="${ttA('healthx.copy_log_title')}" onclick="hxCopyLog()">${tt('healthx.copy_log')}</button>${reload}</div>
    <div class="hxcard ${v.stopped ? 'stop' : problemCount ? 'warn' : 'ok'}"><div class="hxcardhead">${v.stopped ? tt('healthx.crashed') : esc(v.headline || tt('healthx.no_crash'))}</div>
    <div class="hxcardwhy">${v.stopped ? location || esc(v.why || v.headline || '') : problemCount ? ttN('healthx.problems_to_look_at',problemCount) : tt('healthx.log_clean')}</div>
    ${hxNow(v.now)}${hxFixHtml(v.fix,v.file,v.line)}${(v.lines || []).length ? hxFold(tt('healthx.the_lines'),v.lines.join('\n')) : ''}</div>
    ${(v.serious || []).map(w => `<p class="w-warn">${tt('healthx.serious',{w:esc(w)})}</p>`).join('')}
    ${problems.length ? `<h4 class="hxsect">${tt('healthx.sect_problems')}</h4><div class="hxlist">${problems.map(hxLogGroupHtml).join('')}</div>` : ''}
    ${notes.length ? `<details class="hxnotes"${problems.length ? '' : ' open'}><summary>${tt('healthx.sect_notes')} <span class="count">${tt('healthx.sect_notes_hint')}</span></summary><div class="hxlist">${notes.map(hxLogGroupHtml).join('')}</div></details>` : ''}
    ${r.more ? `<p class="count">${ttN('healthx.more_kinds',r.more)}</p>` : ''}</section>`;
}
function hxLogGroupHtml(g){
  const seen = g.seen || [], first = seen[0] || {}, names = g.names || [];
  const plain = g.plain_first || g.plain;
  const original = [g.level,g.area,g.msg,...seen.map(s => [s.line,s.now,s.why].filter(Boolean).join(': '))].filter(Boolean).join('\n');
  return `<div class="hxrow2 ${g.level === 'fatal' ? 'fatal' : g.level === 'warning' || g.level === 'warn' ? 'warning' : ''}"><div class="hxrowmain"><div class="hxrowtitle">${plain ? esc(plain) : `<code>${esc(g.msg)}</code>`}</div>
    ${g.plain_first && names.length > 1 ? `<p>${tt('healthx.same_for',{list:esc(names.slice(1).join(', ') + (g.count > names.length ? ' …' : ''))})}</p>` : g.count > names.length && names.length ? '<span>…</span>' : ''}
    ${hxNow(first.now)}<div class="hxrowmeta"><span class="count">${ttN('healthx.times',g.count || 1)}</span>
    ${g.file ? `<code title="${esc(g.file)}">${esc(g.file.split(/[\\/]/).pop())}</code>` : ''}${first.line ? `<span>${tt('healthx.at_line',{line:first.line})}</span>` : ''}
    ${hxFixHtml(g.fix,g.file,first.line)}</div>${hxFold(tt('healthx.the_games_words'),original)}</div></div>`;
}
async function hxClipboard(text){
  try{ await navigator.clipboard.writeText(text); toast(tt('healthx.copied')); }catch(e){ toast(errText(e)); }
}
function hxCopyLog(){
  const h = state.hl, r = h.log, v = r.verdict || {};
  hxClipboard([h.mod,`${r.errors || 0} / ${r.warnings || 0}`,v.headline || v.why || '',v.now || '',
    ...(r.groups || []).map(g => [g.level,g.plain_first || g.plain || '',ttN('healthx.times',g.count || 1),g.msg].join('\n'))].join('\n\n'));
}
function hxReportHtml(r){
  const strat = r.strat || {}, sf = strat.factions || [], counts = strat.counts || {};
  const totals = [['c_factions',(r.factions || []).length],['c_cultures',(r.cultures || []).length],['c_religions',(r.religions || []).length],['c_units',r.units ? r.units.count : '-'],['c_chains',r.buildings ? r.buildings.chains : '-'],['c_regions',(r.regions || []).length],['c_towns',counts.settlement || 0],['c_characters',counts.character || 0]];
  return `<section class="bsec"><h4>${tt('healthx.report_head',{mod:esc(r.mod),campaign:esc(r.campaign || '-')})}</h4><p class="trnote">${tt('healthx.report_note')}</p>
    <button class="mini" onclick="hxClipboard(state.hl.report.text)">${tt('healthx.copy_markdown')}</button>
    <a class="btn mini" title="${ttA('healthx.files_title')}" download="mod_files.txt" href="/api/modreport/files?mod=${enc(state.hl.mod)}">${tt('healthx.files')}</a>
    ${Object.entries(r.failed || {}).map(([part,why]) => `<p class="w-bad">${tt('healthx.part_failed',{part:esc(part),why:esc(why)})}</p>`).join('')}
    <div class="hxcounts">${totals.map(([key,n]) => `<span><b>${esc(n)}</b> ${tt(HX_REPORT_KEYS[key])}</span>`).join('')}</div>
    <div class="hxtablewrap"><table class="hxtab"><thead><tr>${['c_faction','c_culture','c_religion','c_status','c_towns','c_characters','c_armies'].map(k => `<th>${tt(HX_REPORT_KEYS[k])}</th>`).join('')}</tr></thead><tbody>
    ${(r.factions || []).map(f => { const s = sf.find(s => s.slot === f.slot) || {}; return `<tr><td>${esc(f.label || f.slot)}</td><td>${esc(f.culture || '')}</td><td>${esc(f.religion || '')}</td><td>${esc(s.playable || f.special || '')}</td><td>${(s.towns || []).length}</td><td>${s.characters || 0}</td><td>${s.armies || 0}</td></tr>`; }).join('')}</tbody></table></div>
    ${r.units ? ['by_category','by_class','by_owner'].map(k => `<div class="hxrow"><b>${tt(HX_REPORT_KEYS[k])}</b> ${Object.entries(r.units[k] || {}).map(([name,n]) => `<span>${esc(name)}: ${esc(n)}</span>`).join(' ')}</div>`).join('') : ''}
    ${r.buildings ? `<h4>${tt('healthx.c_chains')} ${r.buildings.chains} · ${tt('healthx.levels',{n:r.buildings.levels})}</h4>${(r.buildings.list || []).map(b => `<div class="hxrow">${esc(b.name)} <span class="count">${tt('healthx.levels',{n:b.levels})}</span></div>`).join('')}` : ''}
    ${sf.length ? `<h4>${tt('healthx.towns_and_people')}</h4>${sf.map(f => `<div class="hxfac"><b>${esc(f.slot)}</b><div>${(f.towns || []).map(t => `${esc(t.region)} (${esc(t.level)})`).join(', ')}</div><div>${(f.named || []).map(n => `${esc(n.name)}${n.rank ? ' (' + esc(n.rank) + ')' : ''}`).join(', ')}</div></div>`).join('')}` : ''}</section>`;
}
function hxDeepHtml(r){
  if(state.hl.deep && state.hl.deep.busy && state.hl.deep.owner !== state.hl) state.hl.deep = null;
  const h = state.hl, sets = r.sets || [], d = h.deep;
  return `<section class="bsec"><h4>${tt('healthx.deep_head')}</h4><p class="trnote">${tt('healthx.deep_note')}</p>
    ${sets.length ? `<label>${tt('healthx.deep_set')} <select id="hxSet">${sets.map(s => `<option value="${esc(s.name)}">${esc(s.name)}${s.mod && s.mod !== h.mod ? ' (' + esc(s.mod) + ')' : ''}</option>`).join('')}</select></label>
    <button class="primary" ${d && d.busy ? 'disabled' : ''} onclick="hxRehearse()">${tt('healthx.deep_run')}</button>` : `<p>${tt('healthx.deep_no_sets')}</p>`}
    ${!d ? '' : d.busy ? `<p>${tt('healthx.deep_busy',{set:esc(d.set)})}</p>` : d.error ? `<p class="w-bad">${esc(d.error)}</p>` : hxDeepResult(d)}</section>`;
}
function hxDeepResult(d){
  return `<h4>${tt('healthx.deep_result',{set:esc(d.set),records:d.records,files:(d.files || []).length,s:(d.ms/1000).toFixed(1)})}</h4>
    <pre class="hxpre">${esc((d.files || []).join('\n'))}</pre>${(d.failed || []).map(f => `<p class="w-bad">${tt('health.could_not_run',{label:esc(f.label),error:esc(f.error)})}</p>`).join('')}
    <h4>${tt('healthx.deep_added')} <span class="count">${(d.added || []).length}</span></h4>${hxFindings(d.added,tt('healthx.deep_none_added'))}
    <h4>${tt('healthx.deep_cleared')} <span class="count">${(d.cleared || []).length}</span></h4>${hxFindings(d.cleared,'-')}
    <p class="count">${tt('healthx.deep_same',{n:d.same})}</p>`;
}
function hxFindings(list,empty){
  if(!(list || []).length) return `<p>${empty}</p>`;
  return `<div class="hllist">${list.map(f => { const sev = HL_SEV[f.severity] || HL_SEV.note; return `<div class="hlrow"><span class="hlsev ${sev[1]}" title="${esc(sev[2])}">${sev[0]}</span><div class="hlmsg">${esc(f.message)}<div class="count">${esc(f.source)} ${esc(f.file || '')}</div></div></div>`; }).join('')}</div>`;
}
async function hxRehearse(){
  const h = state.hl; if(h.deep && h.deep.busy) return;
  const set = document.getElementById('hxSet').value, slot = h.deep = {busy:true,set,owner:h}; hlPaint();
  let r;
  try{ r = await api.post('/api/rehearse',{mod:h.mod,set}); }catch(e){ r = {error:errText(e)}; }
  if(state.hl !== h || h.deep !== slot) return;
  h.deep = r; if(state.mode === 'health' && state.src === h.mod) hlPaint();
}
