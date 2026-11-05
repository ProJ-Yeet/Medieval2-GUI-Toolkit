/* healthx.js - Health's other three tabs (96e2): the game's own log, the
   mod's contents in one report, and a deep check that rehearses a change set

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   The checks tab asks the toolkit's validators about the files. These three
   ask other things: what the game itself said on its last run
   (/api/gamelog), what the mod holds (/api/modreport), and what a change set
   would do to it before it is put on (/api/rehearse, on a linked copy, so
   nothing is written). From the Pfadfinder-Adam campaign editor, ported with
   its author's permission. Every name here starts `hx`.
   ===================================================================== */

const HX_TABS = [
  ['checks', () => tt('healthx.tab_checks')],
  ['log', () => tt('healthx.tab_log')],
  ['report', () => tt('healthx.tab_report')],
  ['deep', () => tt('healthx.tab_deep')],
];

function hxTabsHtml(){
  const h = state.hl;
  return `<div class="hxtabs">${HX_TABS.map(([id, label]) =>
    `<button class="${(h.tab || 'checks') === id ? 'on' : ''}" onclick="hxTab('${id}')">${esc(label())}</button>`).join('')}</div>`;
}

function hxTab(id){
  const h = state.hl;
  h.tab = id;
  if(id === 'log' && !h.log) hxLoad('log', '/api/gamelog?mod=' + enc(h.mod));
  if(id === 'report' && !h.report) hxLoad('report', '/api/modreport?mod=' + enc(h.mod));
  if(id === 'deep' && !h.sets) hxLoad('sets', '/api/rehearse/sets?mod=' + enc(h.mod));
  hlPaint();
}

async function hxLoad(key, url){
  const h = state.hl;
  h[key] = {busy: true};
  let r;
  try{ r = await api.get(url); }catch(e){ r = {error: errText(e)}; }
  if(state.hl !== h) return;
  h[key] = r;
  hlPaint();
}

function hxPanelHtml(){
  const h = state.hl;
  if(h.tab === 'log') return hxLogHtml(h.log);
  if(h.tab === 'report') return hxReportHtml(h.report);
  if(h.tab === 'deep') return hxDeepHtml();
  return '';
}

const hxWait = () => `<div class="empty">${tt('healthx.reading')}</div>`;
const hxErr = r => `<div class="bsec"><div class="w-bad">✗ ${esc(r.error)}</div></div>`;

/* ---- the game's log ---- */
function hxAge(s){
  if(s >= 86400) return ttN('healthx.days_ago', Math.floor(s / 86400));
  if(s >= 3600) return ttN('healthx.hours_ago', Math.floor(s / 3600));
  if(s >= 60) return ttN('healthx.minutes_ago', Math.floor(s / 60));
  return tt('healthx.just_now');
}

/* The game's log as a player reads it (users found the old view hard: the
   engine's own lines first, a tag like [system.run] on every row, and "a
   building lets Y recruit X"). Now: one card saying whether the game crashed
   and why, in plain words, with a button to the unit, building or file to fix;
   then the problems, most frequent first, each a sentence with what it is
   about; the usually-harmless notes folded under them; the game's own words
   behind a fold on every row; and the lot copied for a bug report. */
const hxRelData = rel => { const s = String(rel || '').replace(/\\/g, '/'); const i = s.toLowerCase().lastIndexOf('/data/');
  return i >= 0 ? s.slice(i + 6) : s.replace(/^data\//i, ''); };
const hxShortFile = rel => hxRelData(rel).split('/').pop();
function hxFixBtn(fix, line){
  if(!fix) return '';
  if(fix.kind === 'unit') return `<button class="mini primary" onclick="hxFix('unit','${q1(esc(fix.name))}')">${tt('healthx.fix_unit',{name:esc(fix.name)})}</button>`;
  if(fix.kind === 'building') return `<button class="mini primary" onclick="hxFix('building','${q1(esc(fix.name))}')">${tt('healthx.fix_building',{name:esc(fix.name)})}</button>`;
  return `<button class="mini" onclick="hxFix('file','${q1(esc(hxRelData(fix.name)))}',${+line || 0})">${tt('healthx.fix_file',{file:esc(hxShortFile(fix.name))})}</button>`;
}
async function hxFix(kind, name, line){
  if(state.hl && state.hl.mod && state.src !== state.hl.mod){ state.src = state.hl.mod; }
  if(kind === 'building'){ window.open(`/?mod=${enc(state.src)}&building=${enc(name)}`, '_blank'); return; }
  if(kind === 'file'){ rtOpen(name, line || 0); return; }
  setAppMode('edit');
  for(let i = 0; i < 40 && !(state.data && state.data.units); i++) await new Promise(r => setTimeout(r, 150));
  if(state.data && state.data.units.some(u => u.type === name)) openEditor(name);
  else toast(tt('core.is_not_a_unit_in',{qEdit:name, src:state.src}), 4000);
}
function hxLogRow(g){
  const head = (g.plain_first || g.plain) || esc(g.msg);
  const plain = g.plain_first || g.plain;
  const others = (g.names || []).slice(g.plain_first ? 1 : (g.names || []).length);
  const at = g.seen[0] && g.seen[0].line ? `<span class="count">${tt('healthx.at_line',{line:g.seen[0].line})}</span>` : '';
  const where = g.file ? `<span class="count">${esc(hxShortFile(g.file))}</span>${at}` : '';
  return `<div class="hxrow2 ${g.level}">
      <div class="hxrowmain">
        <div class="hxrowtitle">${plain ? esc(head) : `<code>${esc(g.msg)}</code>`}</div>
        ${others.length ? `<div class="count">${tt('healthx.same_for',{list:others.map(esc).join(', ')})}${g.count > (g.names || []).length ? ' …' : ''}</div>` : ''}
        ${g.file && g.seen[0] && g.seen[0].now ? `<div class="hxnow">${tt('healthx.reads_now')} <code>${esc(g.seen[0].now)}</code></div>` : ''}
        <div class="hxrowmeta">${g.count > 1 ? `<span class="pill">${ttN('healthx.times', g.count)}</span>` : ''}${where}
          ${hxFixBtn(g.fix, g.seen[0] && g.seen[0].line)}</div>
        <details class="hxraw"><summary>${tt('healthx.the_games_words')}</summary>
          <pre class="hxpre">${esc([`[${g.level}] [${g.area}] ${g.msg}`].concat(g.seen.map(x => x.line ? `${tt('healthx.at_line',{line:x.line})} ${x.why}` : x.why)).join('\n'))}</pre></details>
      </div></div>`;
}
function hxLogHtml(r){
  if(!r || r.busy) return hxWait();
  if(r.error) return hxErr(r);
  if(!r.found) return `<div class="bsec"><div class="hxcard"><div class="hxcardhead">${tt('healthx.no_log')}</div>
    <div class="trnote">${esc(r.howto).replace(/\n/g, '<br>')}</div>
    <details><summary class="count">${tt('healthx.looked_in')}</summary><div class="count">${r.looked.map(p => `<code>${esc(p)}</code>`).join('<br>')}</div></details></div></div>`;
  const v = r.verdict;
  const groups = r.groups || [];
  const stopped = v && v.stopped;
  // the bare "the game crashed" line says what the card above already says
  const must = groups.filter(g => g.level !== 'warning' && !(stopped && g.level === 'fatal' && /unspecified error/i.test(g.msg))),
        notes = groups.filter(g => g.level === 'warning');
  let card;
  if(stopped){
    const cause = v.file && v.line
      ? tt('healthx.crash_after_line',{file:esc(hxShortFile(v.file)), line:v.line, col:v.col ? tt('healthx.at_col',{col:v.col}) : ''})
      : esc(String(v.why || v.headline || '').replace(/^the game stopped:\s*/i, ''));
    card = `<div class="hxcard stop"><div class="hxcardhead">✗ ${tt('healthx.crashed')}</div>
      <div class="hxcardwhy">${cause}</div>
      ${v.now ? `<div class="hxnow">${tt('healthx.reads_now')} <code>${esc(v.now)}</code></div>` : ''}
      <div class="hxrowmeta">${hxFixBtn(v.fix, v.line)}</div>
      ${(v.lines || []).length ? `<details class="hxraw"><summary>${tt('healthx.the_lines')}</summary><pre class="hxpre">${esc(v.lines.join('\n'))}</pre></details>` : ''}</div>`;
  }else{
    card = `<div class="hxcard ${must.length ? 'warn' : 'ok'}"><div class="hxcardhead">${must.length ? '⚠' : '✓'} ${v ? esc(v.headline) : tt('healthx.no_crash')}</div>
      <div class="hxcardwhy">${must.length ? ttN('healthx.problems_to_look_at', must.length) : tt('healthx.log_clean')}</div></div>`;
  }
  return `<div class="bsec">
    <div class="hxloghead"><span class="count" title="${esc(r.path)}">${tt('healthx.read_from',{age:hxAge(r.age)})}${r.cut ? ` · ${tt('healthx.log_cut')}` : ''}</span>
      <span style="flex:1"></span>
      <button onclick="hxCopyLog()" title="${ttA('healthx.copy_log_title')}">${tt('healthx.copy_log')}</button>
      <button onclick="hxLoad('log','/api/gamelog?mod='+enc(state.hl.mod))">${tt('health.run_again')}</button></div>
    ${card}
    ${(v && (v.serious || []).length) ? `<div class="count">${v.serious.map(w => tt('healthx.serious',{w:esc(w)})).join('<br>')}</div>` : ''}
    ${must.length ? `<h4 class="hxsect">${tt('healthx.sect_problems')} <span class="n">${must.length}</span></h4>
      <div class="hxlist">${must.map(hxLogRow).join('')}</div>` : ''}
    ${notes.length ? `<details class="hxnotes"${must.length ? '' : ' open'}><summary><h4 class="hxsect">${tt('healthx.sect_notes')} <span class="n">${notes.length}</span></h4>
      <span class="count">${tt('healthx.sect_notes_hint')}</span></summary>
      <div class="hxlist">${notes.map(hxLogRow).join('')}</div></details>` : ''}
    ${r.more ? `<div class="count">${ttN('healthx.more_kinds', r.more)}</div>` : ''}</div>`;
}
/* The log as text for a bug report: the verdict, then each group with its
   plain words and the game's own line. */
async function hxCopyLog(){
  const r = state.hl && state.hl.log;
  if(!r || !r.found) return;
  const v = r.verdict || {}, out = [`Game log (${state.hl.mod}) - ${r.errors} errors, ${r.warnings} warnings`];
  if(v.headline) out.push(v.headline);
  if(v.now) out.push(`${tt('healthx.reads_now')} ${v.now}`);
  out.push('');
  (r.groups || []).forEach(g => {
    out.push(`- [${g.level}] ${(g.plain_first || g.plain || g.msg)}${g.count > 1 ? ` (x${g.count})` : ''}`);
    out.push(`    ${g.msg}`);
  });
  try{ await navigator.clipboard.writeText(out.join('\n')); toast(tt('healthx.copied')); }
  catch(e){ toast('✗ ' + errText(e), 5000); }
}

/* ---- the contents report ---- */
function hxReportHtml(r){
  if(!r || r.busy) return hxWait();
  if(r.error) return hxErr(r);
  const s = r.strat || {}, by = Object.fromEntries((s.factions || []).map(f => [f.slot, f]));
  const u = r.units, b = r.buildings;
  const kv = o => Object.entries(o || {}).map(([k, v]) => `${esc(k)} <b>${v}</b>`).join(' · ');
  const fails = Object.entries(r.failed || {});
  return `<div class="bsec"><h4>${tt('healthx.report_head',{mod:esc(r.mod), campaign:esc(r.campaign || '')})}
      <button style="margin-left:auto" onclick="hxCopyReport()">${tt('healthx.copy_markdown')}</button>
      <a class="btn" href="/api/modreport/files?mod=${enc(state.hl.mod)}" download="mod_files.txt"
        title="${ttA('healthx.files_title')}">${tt('healthx.files')}</a></h4>
    <div class="trnote">${tt('healthx.report_note')}</div>
    ${fails.map(([k, why]) => `<div class="w-bad">${tt('healthx.part_failed',{part:esc(k), why:esc(why)})}</div>`).join('')}
    <div class="hxcounts">
      ${[[tt('healthx.c_factions'), (r.factions || []).length], [tt('healthx.c_cultures'), (r.cultures || []).length],
         [tt('healthx.c_religions'), (r.religions || []).length], [tt('healthx.c_units'), u ? u.count : '-'],
         [tt('healthx.c_chains'), b ? b.chains : '-'], [tt('healthx.c_regions'), (r.regions || []).length],
         [tt('healthx.c_towns'), (s.counts || {}).settlement || 0], [tt('healthx.c_characters'), (s.counts || {}).character || 0]]
        .map(([l, n]) => `<div><span class="n">${n}</span><span class="count">${esc(l)}</span></div>`).join('')}
    </div></div>
    <div class="bsec"><h4>${tt('healthx.c_factions')}</h4><div class="hxtablewrap"><table class="hxtab">
      <tr><th>${tt('healthx.c_faction')}</th><th>${tt('healthx.c_culture')}</th><th>${tt('healthx.c_religion')}</th>
        <th>${tt('healthx.c_status')}</th><th>${tt('healthx.c_towns')}</th><th>${tt('healthx.c_characters')}</th><th>${tt('healthx.c_armies')}</th></tr>
      ${(r.factions || []).map(f => { const x = by[f.slot] || {};
        return `<tr><td>${esc(f.label)}</td><td>${esc(f.culture)}</td><td>${esc(f.religion)}</td>
          <td>${esc(x.playable || f.special || '')}</td><td>${(x.towns || []).length}</td><td>${x.characters ?? ''}</td><td>${x.armies ?? ''}</td></tr>`; }).join('')}
    </table></div></div>
    ${u ? `<div class="bsec"><h4>${tt('healthx.c_units')} <span class="n">${u.count}</span></h4>
      <div class="count">${tt('healthx.by_category')} ${kv(u.by_category)}</div>
      <div class="count">${tt('healthx.by_class')} ${kv(u.by_class)}</div>
      <div class="count">${tt('healthx.by_owner')} ${kv(u.by_owner)}</div></div>` : ''}
    ${b ? `<div class="bsec"><h4>${tt('healthx.c_chains')} <span class="n">${b.chains}</span> <span class="count">${tt('healthx.levels',{n:b.levels})}</span></h4>
      <div class="count">${b.list.map(c => `${esc(c.name)} (${c.levels})`).join(', ')}</div></div>` : ''}
    ${(s.factions || []).length ? `<div class="bsec"><h4>${tt('healthx.towns_and_people')}</h4>
      ${s.factions.filter(f => f.towns.length || f.named.length).map(f => `<div class="hxfac"><b>${esc(f.slot)}</b>
        <div class="count">${f.towns.map(t => `${esc(t.region)} <i>${esc(t.level || '')}</i>`).join(', ')}</div>
        <div class="count">${f.named.map(c => esc(c.name) + (c.rank ? ` (${esc(c.rank)})` : '')).join(', ')}</div></div>`).join('')}</div>` : ''}`;
}

async function hxCopyReport(){
  const r = state.hl.report;
  if(!r || !r.text) return;
  try{ await navigator.clipboard.writeText(r.text); toast(tt('healthx.copied')); }
  catch(e){ toast('✗ ' + errText(e), 5000); }
}

/* ---- the deep check ---- */
function hxDeepHtml(){
  const h = state.hl, s = h.sets;
  if(!s || s.busy) return hxWait();
  if(s.error) return hxErr(s);
  const d = h.deep;
  const sets = s.sets || [];
  return `<div class="bsec"><h4>${tt('healthx.deep_head')}</h4>
    <div class="trnote">${tt('healthx.deep_note')}</div>
    ${sets.length ? `<div class="hxrow"><label for="hxSet">${tt('healthx.deep_set')}</label>
      <select id="hxSet">${sets.map(x => `<option value="${esc(x.name)}" ${x.mod === h.mod ? '' : ''}>${esc(x.name)}${
        x.mod && x.mod !== x.name ? ` (${esc(x.mod)})` : ''}</option>`).join('')}</select>
      <button class="primary" ${d && d.busy ? 'disabled' : ''} onclick="hxDeepRun()">${tt('healthx.deep_run')}</button></div>`
      : `<div class="count">${tt('healthx.deep_no_sets')}</div>`}
  </div>${hxDeepResultHtml(d)}`;
}

async function hxDeepRun(){
  const h = state.hl, set = (document.getElementById('hxSet') || {}).value;
  if(!set) return;
  h.deep = {busy: true, set};
  hlPaint();
  let r;
  try{ r = await api.post('/api/rehearse', {mod: h.mod, set}); }catch(e){ r = {error: errText(e)}; }
  if(state.hl !== h) return;
  h.deep = r;
  hlPaint();
}

function hxDeepResultHtml(d){
  if(!d) return '';
  if(d.busy) return `<div class="empty">${tt('healthx.deep_busy',{set:esc(d.set)})}</div>`;
  if(d.error) return hxErr(d);
  const row = f => { const [icon, cls] = HL_SEV[f.severity] || HL_SEV.note;
    return `<div class="hlrow"><span class="hlsev ${cls}">${icon}</span><div class="hlmsg">${esc(f.message)}
      <div class="count">${esc(f.source)}${f.file ? ` · <code>${esc(f.file)}</code>` : ''}</div></div></div>`; };
  return `<div class="bsec"><h4>${tt('healthx.deep_result',{set:esc(d.set), records:d.records, files:d.files.length, s:(d.ms/1000).toFixed(1)})}</h4>
    <div class="count">${d.files.map(f => `<code>${esc(f)}</code>`).join(' ')}</div>
    ${(d.failed || []).map(s => `<div class="w-bad">${tt('health.could_not_run',{label:esc(s.label), error:esc(s.error)})}</div>`).join('')}
    <h4>${tt('healthx.deep_added')} <span class="n">${d.added.length}</span></h4>
    <div class="hllist">${d.added.map(row).join('') || `<div class="trnote">${tt('healthx.deep_none_added')}</div>`}</div>
    <h4>${tt('healthx.deep_cleared')} <span class="n">${d.cleared.length}</span></h4>
    <div class="hllist">${d.cleared.map(row).join('') || `<div class="count">-</div>`}</div>
    <div class="count">${tt('healthx.deep_same',{n:d.same})}</div></div>`;
}
