/* battleflags.js - Battle banners: descr_banners_new.xml

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* ========================= BATTLE BANNERS (65) =========================
   The banner a unit carries in battle. Three lists of named banners - the
   names an EDU unit's `banner faction|unit|holy` lines use - each holding a
   row per faction with its texture, then the royal banner, then the look of
   all of them under Settings. A faction's units carry no banner of theirs
   when the banner their EDU line names has no row for it, which is the
   warning that matters here.

   THE PAGE NEVER PARSES A GAME FILE: /api/battleflags and its plan|apply.

   The file and its routes say "battleflags", never "banners": an ad blocker's
   list blocks any URL ending /banners.js or holding /banners/, the request never
   leaves the browser, and the whole UI stops at "did not finish loading". */

const BNX_SECTIONS = [
  {tag: 'FactionBanners', label: tt('battleflags.faction_banners'), edu: tt('battleflags.banner_faction')},
  {tag: 'UnitSpecificBanners', label: tt('battleflags.unit_banners'), edu: tt('battleflags.banner_unit')},
  {tag: 'HolyBanners', label: tt('battleflags.holy_banners'), edu: tt('battleflags.banner_holy')},
  {tag: 'RoyalBanner', label: tt('battleflags.royal_banner'), edu: ''},
];

async function loadBanners(){
  const mod = state.src;
  main.innerHTML = `<div class="empty">${tt('common.reading')} ` + esc(mod) + `${tt('battleflags.s_battle_banners')}</div>`;
  let r;
  try{ r = await api.get('/api/battleflags?mod=' + enc(mod)); }
  catch(e){ if(stale('banners', mod)) return;
    main.innerHTML = `<div class="empty">${tt('common.couldnt_read_them')}<br><span class="count">${esc(errText(e))}</span>
      <br><br><button class="primary" onclick="loadBanners()">${tt('common.retry')}</button></div>`; return; }
  if(stale('banners', mod)) return;
  const keep = state.bnx && state.bnx.mod === mod ? state.bnx : null;
  state.bnx = Object.assign({mod, sel: keep ? keep.sel : '', w: bnxBlank(), busy: false}, r);
  if(!state.bnx.sel && (r.banners || []).length) state.bnx.sel = String(r.banners.find(b => b.units)?.id ?? r.banners[0].id);
  renderBanners();
}
function bnxBlank(){ return {attrs: {}, add_rows: [], remove_rows: [], trim: false}; }
function bnxChanged(){
  const w = state.bnx.w;
  return Object.values(w.attrs).reduce((s, o) => s + Object.keys(o).length, 0)
    + w.add_rows.length + w.remove_rows.length + (w.trim ? 1 : 0);
}

function renderBanners(){
  const c = state.bnx;
  if(!c){ loadBanners(); return; }
  const strip = minorTabsHtml('', 'data/descr_banners_new.xml');
  const find = (c.findings || []).map(f => Object.assign({}, f, {name: f.key}));
  const n = bnxChanged();
  const left = c.error ? `<div class="count" style="padding:8px">${esc(c.error)}.</div>`
    : `<button class="trrow${c.sel === 'settings' ? ' on' : ''}" onclick="bnxPick('settings')">
        <div class="nm">${tt('battleflags.settings')}</div><div class="sub">${tt('battleflags.scale_colours_and_the_wave_for')}</div></button>`
      + BNX_SECTIONS.map(s => {
          const list = (c.banners || []).filter(b => b.section === s.tag);
          if(!list.length) return '';
          return `<div class="trnote"><b>${s.label}</b>${s.edu ? ` <span class="count"><code>${s.edu}</code></span>` : ''}</div>`
            + list.map(b => `<button class="trrow${c.sel === String(b.id) ? ' on' : ''}" onclick="bnxPick('${b.id}')">
              <div class="nm">${esc(b.name)}</div>
              <div class="sub">${b.rows.length} row(s)${s.edu ? tt('battleflags.unit_s_carry_it',{units:b.units}) : ''}${bnxDirty(b) ? ` ${tt('common.changed')}` : ''}</div></button>`).join('');
        }).join('');
  main.innerHTML = strip + `<div class="trwrap">
    <div class="trlist">
      ${findingsHtml('banners', find, 'bnxOpen')}
      <div class="trrows">${left}</div>
    </div>
    <div class="trmain">
      <div class="cdbhead"><div>${tt('battleflags.descr_banners_new_xml_the_banner')}</div>
        <span style="flex:1"></span>
        <button onclick="bnxRevert()" ${n ? '' : 'disabled'}>${tt('common.revert')}</button>
        <button class="primary" onclick="bnxSave()" ${n ? '' : 'disabled'}>${tt('battleflags.save_change',{x:n || '',x2:n === 1 ? '' : 's'})}</button>
      </div>
      ${c.trailing_lines ? `<div class="trnote">${tt('battleflags.line_s_follow_banners_the_game',{trailing_lines:c.trailing_lines})}
        <button onclick="bnxTrim()">${c.w.trim ? tt('battleflags.keep_them') : tt('battleflags.cut_them_off_on_save')}</button></div>` : ''}
      ${c.error ? '' : c.sel === 'settings' ? bnxSettingsHtml() : bnxBannerHtml()}
    </div>
  </div>`;
}

function bnxDirty(b){
  const w = state.bnx.w;
  return w.attrs[b.id] || b.rows.some(r => w.attrs[r.id] || w.remove_rows.includes(r.id))
    || w.add_rows.some(a => b.rows.some(r => r.id === a.like));
}
function bnxPick(s){ state.bnx.sel = String(s); renderBanners(); }
function bnxOpen(key){
  const [kind, rest] = String(key).split(/\/(.*)/);
  const c = state.bnx;
  if(kind === 'banner') c.sel = rest;
  else if(kind === 'setting') c.sel = 'settings';
  else if(kind === 'faction'){
    const b = (c.banners || []).find(x => x.rows.some(r => r.faction === rest));
    if(b) c.sel = String(b.id);
  } else if(kind === 'path'){
    const b = (c.banners || []).find(x => Object.values(x.attrs).includes(rest)
      || x.rows.some(r => Object.values(r.attrs).includes(rest)));
    if(b) c.sel = String(b.id);
  }
  renderBanners();
}
function bnxRevert(){ state.bnx.w = bnxBlank(); renderBanners(); }
function bnxTrim(){ state.bnx.w.trim = !state.bnx.w.trim; renderBanners(); }

function bnxVal(id, a, v){
  const e = state.bnx.w.attrs[id];
  return e && e[a] !== undefined ? e[a] : v;
}
function bnxSet(id, a, v, was){
  const w = state.bnx.w.attrs, e = w[id] = w[id] || {};
  if(v.trim() === was) delete e[a]; else e[a] = v.trim();
  if(!Object.keys(e).length) delete w[id];
  renderBanners();
}
function bnxBox(id, a, v, width){
  return `<input style="width:${width}px" value="${esc(bnxVal(id, a, v))}"
    onchange="bnxSet(${id}, '${q1(esc(a))}', this.value, '${q1(esc(v))}')">`;
}

function bnxSettingsHtml(){
  const c = state.bnx;
  return `<div class="cdbsec"><h3>${tt('battleflags.settings')}</h3>
    <table class="smxtab">${(c.settings || []).map(s => `<tr><td><code>${esc(s.path)}</code></td><td>${
      Object.entries(s.attrs).map(([k, v]) => `<span class="count">${esc(k)}</span> ${bnxBox(s.id, k, v, 60)}`).join(' ')}</td></tr>`).join('')}
    </table>
    <div class="count">${tt('battleflags.the_colours_are_0_to_255')}</div></div>`;
}

function bnxBannerHtml(){
  const c = state.bnx, b = (c.banners || []).find(x => String(x.id) === c.sel);
  if(!b) return `<div class="count" style="padding:8px">${tt('battleflags.pick_a_banner')}</div>`;
  const sec = BNX_SECTIONS.find(s => s.tag === b.section) || {};
  const paths = b.rows.length ? Object.keys(b.rows[0].attrs).filter(k => k !== 'Faction') : [];
  const have = new Set(b.rows.map(r => r.faction.toLowerCase()));
  const missing = (c.roster || []).filter(f => !have.has(f) && !c.w.add_rows.some(a => a.faction.toLowerCase() === f
    && b.rows.some(r => r.id === a.like)));
  const head = Object.entries(b.attrs).filter(([k]) => k !== 'Name');
  return `<div class="cdbsec"><h3>${tt('battleflags.line',{name:esc(b.name),x:sec.label || '',x2:sec.edu
      ? ` ${tt('battleflags.on_unit_s',{edu:sec.edu,name:esc(b.name),units:b.units})}` : '',line:b.line})}</h3>
    ${head.length ? `<table class="smxtab">${head.map(([k, v]) => `<tr><td><code>${esc(k)}</code></td>
      <td>${bnxBox(b.id, k, v, /Mesh$/.test(k) ? 340 : 70)}</td></tr>`).join('')}</table>` : ''}
    <h3>${tt('battleflags.a_row_per_faction')} <span class="count">${b.rows.length}</span></h3>
    <table class="smxtab"><tr><th>${tt('common.faction')}</th>${paths.map(k => `<th>${esc(k)}</th>`).join('')}<th></th></tr>
    ${b.rows.map(r => {
      const gone = c.w.remove_rows.includes(r.id);
      return `<tr${gone ? ' style="opacity:.45"' : ''}><td>${bnxBox(r.id, tt('common.faction'), r.faction, 110)}</td>
        ${paths.map(k => `<td>${r.attrs[k] !== undefined ? bnxBox(r.id, k, r.attrs[k], k === 'Mesh' ? 200 : 290) : ''}</td>`).join('')}
        <td><button onclick="bnxDrop(${r.id})">${gone ? 'keep' : '✕'}</button></td></tr>`;
    }).join('')}
    ${c.w.add_rows.filter(a => b.rows.some(r => r.id === a.like)).map(a =>
      `<tr><td colspan="${paths.length + 2}" class="count">${tt('battleflags.copied_from_on_save',{faction:esc(a.faction),x:esc(b.rows.find(r => r.id === a.like).faction)})}</td></tr>`).join('')}
    </table>
    ${b.rows.length ? `<div class="trnote">${tt('battleflags.add_a_row_for_copied_from',{x:missing.length ? `<select id="bnxNewFac">${missing.map(f => `<option>${esc(f)}</option>`).join('')}</select>`
        : `<input id="bnxNewFac" placeholder="${ttA('common.faction_2')}" style="width:110px">`})} <select id="bnxLike">${b.rows.map(r => `<option value="${r.id}">${esc(r.faction)}</option>`).join('')}</select>
      <button onclick="bnxAdd()">${tt('common.add')}</button>
      <div class="count">${tt('battleflags.the_copy_points_at_the_same')}</div></div>` : ''}
  </div>`;
}
function bnxDrop(id){
  const r = state.bnx.w.remove_rows, i = r.indexOf(id);
  if(i >= 0) r.splice(i, 1); else r.push(id);
  renderBanners();
}
function bnxAdd(){
  const fac = (document.getElementById('bnxNewFac').value || '').trim();
  const like = +document.getElementById('bnxLike').value;
  if(!fac) return;
  const b = state.bnx.banners.find(x => x.rows.some(r => r.id === like));
  const donor = b.rows.find(r => r.id === like).faction;
  const name = /^[A-Z]/.test(donor) ? fac.charAt(0).toUpperCase() + fac.slice(1) : fac;
  state.bnx.w.add_rows.push({like, faction: name});
  renderBanners();
}

async function bnxSave(){
  const c = state.bnx;
  if(c.busy) return;
  const body = Object.assign({mod: state.src, sig: c.sig || ''}, c.w);
  c.busy = true;
  let plan;
  try{ plan = await api.post('/api/battleflags/plan', body); }
  catch(e){ plan = {error: errText(e)}; }
  finally{ c.busy = false; }
  if(plan.error){ toast('✗ ' + plan.error, 8000); return; }
  const p = plan.plan || {};
  if(!confirm(tt('battleflags.write_change_s',{n:(p.changes || []).length}) + (p.changes || []).slice(0, 16).join('\n')
    + ((p.warnings || []).length ? '\n\n⚠ ' + p.warnings.slice(0, 5).join('\n⚠ ') : '')
    + tt('common.backed_up_first_and_log_can'))) return;
  let res;
  try{ res = await api.post('/api/battleflags/apply', body); }
  catch(e){ res = {error: errText(e)}; }
  if(res.error){ toast('✗ ' + res.error, 8000); return; }
  toast(tt('common.saved_log_can_undo_it'));
  await loadBanners();
}
