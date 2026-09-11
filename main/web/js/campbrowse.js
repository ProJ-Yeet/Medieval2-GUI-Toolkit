/* campbrowse.js - Campaign Map: which campaign, and what is in each one

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */
/* =====================================================================
   THE CAMPAIGN BROWSER - Phase 20b, D14.

   Every name here starts `cbr`, and none of them existed anywhere else in the
   tree before this phase.

   WHAT THIS ACTUALLY FIXED, WHICH IS MORE THAN THE ITEM ASKED FOR. D14 was
   filed as cosmetic: "a screen listing every campaign in the mod with what is
   in each one, before you pick one", over a picker that already existed. It
   turned out the picker did not exist and the list it would have been built on
   was wrong. `campstrat.campaigns` reads the folders DIRECTLY under
   world/maps/campaign, and both mods installed here keep a whole second
   campaign one level down - Divide and Conquer's Shattered_Alliances (30
   factions, 199 settlements, 25 playable) and Third Age Reforged's Fellowship
   campaign (16 factions, 129 settlements, and ten map layers of its own).
   Every route on this screen has taken a `&campaign=` since 16g and every one
   of them resolves a name with a slash in it. The only thing that made those
   two campaigns unreachable was that nothing ever offered them.

   SO PICKING ONE IS THE FEATURE, AND THE LIST IS HOW YOU PICK. `cmapSetCampaign`
   in campmap.js is what a pick calls: the screen owns which campaign it is
   reading and owns knowing what a change to it invalidates. This file lists,
   describes and asks; it does not reach into another panel's state.

   THE ROW SAYS WHAT THE ENGINE WOULD SAY, NOT WHAT WE HOPE. Three things on it
   are measured facts about real mods rather than fields in a format: a campaign
   whose folder name and whose `campaign` line disagree (DaC's nested one says
   `imperial_campaign` on its first line), a campaign that ships map layers of
   its own (which the map screen reads when that campaign is open, since the
   follow-up to 22b; before it, the screen drew world/maps/base always), and a
   campaign nothing has ever named on the new-game menu. Each of those is a
   thing somebody would otherwise find out much later.
   ===================================================================== */

//: The counts on a row, in the order they answer "how big is this campaign".
//: `resource` is deliberately last: DaC writes 1,131 of them and the number
//: says more about the map than about the campaign.
const CBR_COUNTS = [
  ['faction', 'factions'], ['settlement', 'settlements'],
  ['character', 'characters'], ['fort', 'forts'],
  ['watchtower', 'watchtowers'], ['resource', 'resources'],
];

/* ---------- state ----------

   Beside `state.cmap` like every other panel here, and read once per mod: the
   parse of every campaign's descr_strat.txt is 35 to 150 ms on the mods
   installed here, which is cheap enough to do on the click that opens the
   panel and far too much to do with the map. */
function cbrNew(mod){
  return {mod, open: false, loading: false, err: '', d: null};
}

function cbrOpen(){
  const c = state.cmap;
  if(!c) return;
  if(!state.cbr || state.cbr.mod !== c.mod) state.cbr = cbrNew(c.mod);
  cbrPaint();
}

function cbrToggle(){
  const k = state.cbr;
  if(!k) return;
  k.open = !k.open;
  activity('campaign browser',
           k.open ? 'opened the campaign browser' : 'closed it');
  if(k.open && !k.d && !k.loading) cbrLoad();
  else cbrPaint();
}

async function cbrLoad(){
  const k = state.cbr, c = state.cmap;
  if(!k || !c) return;
  k.loading = true; k.err = '';
  cbrPaint();
  let d;
  try{
    d = await api.get(`/api/map/campaigns?mod=${enc(k.mod)}`,
                      {label: 'reading this mod’s campaigns'});
  }catch(e){
    if(state.cbr !== k) return;
    k.loading = false; k.err = errText(e); cbrPaint(); return;
  }
  if(state.cbr !== k) return;
  k.loading = false;
  k.d = d;
  cbrPaint();
}

//: Which campaign the screen is reading. An empty `c.campaign` means the
//: server's own fallback, so the row for that one is the one shown as open.
function cbrCurrent(){
  const c = state.cmap, k = state.cbr;
  if(!c) return '';
  return c.campaign || (k && k.d && k.d.default) || '';
}

/* Open one. Everything that follows from it belongs to the screen.

   The confirm is not ceremony: switching campaign re-reads descr_strat.txt and
   drops what every panel over it has loaded, and one of those panels may have
   a form open with typing in it. Asking once is cheaper than losing it. */
function cbrPick(rel){
  if(!state.cmap || rel === cbrCurrent()) return;
  cmapSetCampaign(rel);
}

/* ---------- drawing ---------- */

function cbrPaint(){
  const el = document.getElementById('cmCamps');
  if(!el) return;
  el.innerHTML = cbrHtml();
}

function cbrHtml(){
  const k = state.cbr;
  if(!k) return '';
  const d = k.d, here = cbrCurrent();
  const rows = (d && d.campaigns) || [];
  const shown = rows.find(r => r.campaign === here);
  const head = `<div class="cpbar">
    <button class="cptog${k.open ? ' on' : ''}" onclick="cbrToggle()"
      title="Every campaign this mod ships, with what is in each one, and which of them this screen is reading."
      >\u{1F3F0} Campaign${k.open ? ' ✓' : ''}</button>
    <span class="count">${shown
      ? esc(shown.title || shown.leaf)
      : esc(here || 'imperial_campaign')}${rows.length > 1
        ? ` · ${rows.length} in this mod` : ''}</span>
    ${k.loading ? '<span class="count">reading…</span>' : ''}
  </div>${typeof cmapHomeNote === 'function' ? cmapHomeNote() : ''}`;
  if(!k.open) return head;
  if(k.err) return head + `<div class="cbrpanel w-bad">${esc(k.err)}</div>`;
  if(!d) return head + `<div class="cbrpanel count">reading every
    <code>descr_strat.txt</code> in this mod…</div>`;
  if(!rows.length) return head + `<div class="cbrpanel count">
    ${esc(k.mod)} has no campaign at all: nothing under
    <code>${esc(d.dir)}</code> holds a <code>descr_strat.txt</code>. The map
    itself still reads, because the layers and the region list are in
    <code>${esc(d.base)}</code> and belong to the map rather than to a
    campaign.</div>`;
  return head + `<div class="cbrpanel">
    ${cbrDescrHtml(d)}
    ${rows.map(r => cbrRowHtml(r, r.campaign === here)).join('')}
    <div class="count">${rows.length} campaign${rows.length === 1 ? '' : 's'}
      read in ${d.ms} ms. The ten map layers and the region list are in
      <code>${esc(d.base)}</code> for every campaign that ships no copy of
      its own - what changes between those is who starts where, with what, and
      against whom.</div>
  </div>`;
}

//: 16f's rule about a rule with no evidence, on the one field most likely to
//: be empty. The stock game keeps campaign_descriptions.txt inside its packed
//: data, and "no title" and "no file to have a title in" are different states.
function cbrDescrHtml(d){
  const s = d.descriptions || {};
  if(s.have) return '';
  return `<div class="count">Nothing in <code>${esc(s.file || '')}</code> to
    read a menu title out of - this mod ships neither it nor the compiled
    archive beside it - so no campaign below shows one. That is the file
    missing, not the campaigns being unnamed.</div>`;
}

function cbrRowHtml(r, open){
  const c = r.counts || {}, v = r.values || {}, ros = r.rosters || {};
  const play = (ros.playable || []).length;
  const unlock = (ros.unlockable || []).length;
  const non = (ros.nonplayable || []).length;
  const counts = CBR_COUNTS.filter(([k]) => c[k])
    .map(([k, label]) => `${c[k].toLocaleString()} ${label}`).join(' · ');
  return `<div class="cbrrow${open ? ' on' : ''}">
    <div class="cbrnm">
      <b>${esc(r.title || r.leaf)}</b>
      ${open ? '<span class="cpun">open</span>'
        : `<button onclick="cbrPick('${esc(r.campaign).replace(/'/g, "&#39;")}')"
            title="Read this campaign instead">Open</button>`}
    </div>
    <div class="count"><code>${esc(r.folder)}</code>${r.default
      ? ' · the one every route falls back to' : ''}</div>
    ${!r.read ? `<div class="w-bad">${esc(r.problem)}</div>` : `
      <div class="count">${esc(v.start_date || '?')} to
        ${esc(v.end_date || '?')}${v.timescale
          ? ` · ${esc(v.timescale)} years a turn` : ''} ·
        ${r.lines.toLocaleString()} lines</div>
      <div class="count">${play} playable · ${unlock} unlockable ·
        ${non} not playable</div>
      ${counts ? `<div class="count">${counts}</div>` : ''}
      ${r.renamed ? `<div class="count">Its folder is
        <b>${esc(r.leaf)}</b> and its first line says
        <b>campaign ${esc(r.name)}</b>. Both names are real - a mod's own files
        point at one or the other.</div>` : ''}
      ${r.problems ? `<div class="w-warn">${r.problems} line${
        r.problems === 1 ? '' : 's'} of it did not parse. Every one is reported
        with its number by the validator.</div>` : ''}
      ${cbrFilesHtml(r)}
      ${r.layers.length ? `<div class="count">It ships ${r.layers.length}
        map layer${r.layers.length === 1 ? '' : 's'} of its own
        (${esc(r.layers.slice(0, 3).join(', '))}${r.layers.length > 3
          ? ', …' : ''}), which the engine reads instead of the base's. Open,
        this screen draws those.</div>` : ''}`}
  </div>`;
}

//: Which of the campaign folder's files it has. The absent ones are the point:
//: a campaign with no descr_mercenaries.txt hires from the base map's pools,
//: and a panel that offered a pool picker for it would be offering nothing.
function cbrFilesHtml(r){
  const missing = (r.files || []).filter(f => !f.have);
  if(!missing.length) return '';
  return `<div class="count">No ${missing.map(f =>
    `<code>${esc(f.file)}</code>`).join(', ')} of its own - ${
    missing.length === 1 ? esc(missing[0].why) + ' comes from elsewhere'
      : 'those come from elsewhere'}.</div>`;
}
