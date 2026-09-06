/* core.js - shared state, the API client, the module registry and the burger
   menu, mod loading, filters, and the card grid every mode paints into

   Part of the Medieval 2 GUI Toolkit UI. These files are plain
   <script> tags sharing ONE global scope, loaded in the order set in
   index.html - there is no build step and no module system. Two rules
   follow from that: a top-level name must be unique across all of
   them, and a file's top-level side effects may not depend on a file
   loaded after it. */

/* ---------- the files this page is made of ----------
   One dropped <script> used to look like a dead server.

   index.html asks for two dozen files at once, and the page loads whether or
   not they all arrive: a missing one leaves its module's functions simply
   absent, so the first call into it throws a ReferenceError far from the cause
   - and the startup screen said the server could not be reached, while that
   server's own log showed every request of that same second answered. It is
   the one place the reader would never look.

   iconRetry below already refetches a dropped unit card for exactly this
   reason. A dropped module is the same accident with a worse ending, so it
   gets the same answer: fetch it again, in the order index.html lists them
   (a file may not depend on one loaded after it), and only give up out loud,
   naming the file, once it really will not come. */
const uiFailedFiles=[];
// A resource error does not bubble, so this is a CAPTURING listener on window -
// the one place that sees it. core.js is first in index.html precisely so this
// is armed before any of the others are fetched.
window.addEventListener('error',e=>{
  const t=e.target;
  if(t&&t.tagName==='SCRIPT'&&t.src)uiFailedFiles.push(t.src);
},true);

const UI_RETRIES=3;
let uiStarted=false;
// The order the page asked for them in, which is the order they must run in.
const uiScriptOrder=()=>[...document.querySelectorAll('script[src]')].map(s=>s.src);

// `async=false` is not a stray line: a script element created here is async BY
// DEFAULT and would run whenever it happened to land.
function loadUiFile(src,attempt){
  return new Promise((done,fail)=>{
    const s=document.createElement('script');
    s.async=false;
    // Same trick as iconRetry: ask for a URL the browser has not already
    // written off as failed.
    s.src=src.split('#')[0]+'#retry'+attempt;
    s.onload=()=>done();
    s.onerror=()=>fail(new Error(src));
    document.head.appendChild(s);
  });
}

async function retryDroppedUiFiles(){
  const order=uiScriptOrder();
  // boot.js is skipped: all it does is call startUi, which is already running.
  const todo=[...new Set(uiFailedFiles)].filter(s=>!s.split('#')[0].endsWith('/boot.js'))
    .sort((a,b)=>order.indexOf(a)-order.indexOf(b));
  uiFailedFiles.length=0;
  const lost=[];
  for(const src of todo){
    let got=false;
    for(let i=1;i<=UI_RETRIES&&!got;i++){
      try{ await loadUiFile(src,i); got=true; }
      catch(e){ await new Promise(r=>setTimeout(r,120*i*i)); }
    }
    if(!got)lost.push(src);
  }
  return lost;
}

function uiLoadFailed(lost){
  const names=lost.map(s=>s.split('/').pop().split('#')[0]).join(', ');
  main.innerHTML=`<div class="empty">The tool did not finish loading.<br>
    <span class="count">The server is running - it answered for the rest of this page -
    but the browser never received ${names?`<b>${esc(names)}</b>`:'part of the interface'}.
    Reloading fetches it again.</span><br><br>
    <button class="primary" onclick="location.reload()">Reload the page</button></div>`;
}

/* Start the app once every file it is made of is actually here.

   boot.js calls this, and so does window's load event - because boot.js is one
   of the two dozen and can be the file that goes missing, in which case nothing
   would ever start at all. Whichever gets here first wins. */
async function startUi(){
  if(uiStarted)return;
  uiStarted=true;
  const lost=uiFailedFiles.length?await retryDroppedUiFiles():[];
  if(lost.length)return uiLoadFailed(lost);
  wireKeepPlace();
  init();
}
window.addEventListener('load',()=>startUi());

// `dst` is the mod being written to right now, which a single-mod mode mirrors
// onto the source. `xferDst` is the destination the user actually PICKED, kept
// apart so that entering Edit/Buildings doesn't quietly overwrite it - see
// applyMode.
const state={mods:[],src:null,dst:null,xferDst:null,data:null,destData:null,factionNames:{},
  sel:{faction:new Set(),category:new Set(),class:new Set(),era:new Set()},
  selMode:false, selected:new Set(), cfg:{}, editing:null, settings:{},
  // group headings the user has folded shut, `groupBy:heading` (see toggleGroup)
  folded:new Set(),
  // 'transfer' = move units between mods; 'edit' = edit the units of ONE mod;
  // 'bmdb' = edit / clean up that mod's whole battle_models.modeldb;
  // 'sounds' = which voice-bank entry each unit uses;
  // 'buildings' = that mod's export_descr_buildings.txt
  // 'traits' = its export_descr_character_traits.txt, both halves;
  // 'ancillaries' = its export_descr_ancillaries.txt, likewise;
  // 'minor' = the five small campaign files (rebels, religions, resources,
  //           cultures, character names) behind one tab strip
  mode:'home', ed:null, bmdb:null, clean:null, snd:null, destSnd:null, str:null,
  tr:null, an:null, mf:null, fac:null,
  // bld survives a hop into the unit editor and back - see openUnitFromBuilding
  bld:null, bldReturn:null,
  // the modules opened before this one, oldest first - what the Back button
  // walks out through once every dialog above it is shut (see NAV_LAYERS)
  modeTrail:[]};

const VANILLA_UNIT_LIMIT=500;   // M2TW vanilla EDU cap; M2TWEOP/EOP raise it.
const VANILLA_FACTION_LIMIT=31; // M2TW vanilla descr_sm_factions cap; M2EX raises it.

/* ---------- the API client ----------
   Two things every request in this app needs, so they live here rather than in
   twenty modules: it can be ABANDONED (picking another mod half way through a
   load must not paint the mod you just left), and it is what the loading bar
   watches. A module gets both by doing nothing at all - see `loadbar` below. */

// Thrown by a request that was abandoned. Callers check for it and return
// quietly: nothing went wrong, the answer simply stopped being wanted.
const ABORTED='__aborted__';
const isAborted=e=>e===ABORTED||(e&&e.name==='AbortError');
// Bumped by every new load. A response carrying an older number is dropped
// instead of painted - the reason a fast switch back and forth can't leave the
// screen showing the other mod.
let _loadGen=0,_loadAbort=null;
function newLoad(){
  _loadGen++;
  if(_loadAbort)_loadAbort.abort();      // the requests of the load being replaced
  _loadAbort=new AbortController();
  return {gen:_loadGen,signal:_loadAbort.signal};
}
const loadStale=gen=>gen!==_loadGen;

// GET with a few automatic retries - a page's request can be dropped transiently
// (e.g. during an icon burst, or if the tab was open across a server restart),
// and we must never hang forever on such a blip. An abandoned request is never
// retried: nobody is waiting for it.
const api={
  get:async(u,opts)=>{
    const o=(typeof opts==='number')?{tries:opts}:(opts||{});
    const tries=o.tries||4; let err;
    loadbar.opened(u,o.label);
    try{
      for(let i=0;i<tries;i++){
        try{const r=await fetch(u,{cache:'no-store',signal:o.signal});
          if(!r.ok) throw await httpAnswer(r);
          return await r.json();}
        catch(e){
          if(isAborted(e)||(o.signal&&o.signal.aborted))throw ABORTED;
          err=e;
          if(e.deliberate)break;   // an answer, not a blip - asking again changes nothing
          if(i<tries-1) await new Promise(res=>setTimeout(res,200*(i+1)));}
      }
      throw apiFailed(err,u);
    }finally{loadbar.closed(u);}},
  post:async(u,b,opts)=>{
    const o=opts||{};
    loadbar.opened(u,o.label);
    try{
      return await (await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify(b||{}),signal:o.signal})).json();
    }catch(e){ if(isAborted(e))throw ABORTED; throw apiFailed(e,u); }
    finally{loadbar.closed(u);}}};

/* Say what a failed request actually was.

   Three different things used to arrive at a caller as the same bare error, and
   the startup screen read all three as "the server isn't running": nothing
   answered (it really is gone), it answered and said no (it is running, and the
   reason is in its log), or the request was never made because the code asking
   for it is broken. Only the first is worth sending someone back to the
   launcher window, so each carries its own mark from here on. */
/* What the server said, and whether asking again could change it.

   A non-OK reply used to become the string "HTTP 500" and then be retried four
   times. Both halves were wrong. The reply carries the reason in its body -
   which file, which line, what to fix - and that is the only thing worth
   putting on the screen; and a 404 or a 409 is an answer the server chose, so
   three more of them only put three more stack traces in its log and make the
   wait four times longer. A dropped request is not this: it fails with no
   status at all and is still retried, which is what the retries were for.
   502/503/504 stay retryable too - that is the shape of a server still coming
   up. */
async function httpAnswer(r){
  let said='';
  try{ const b=await r.json(); said=(b&&b.error)||''; }catch(e){}
  const err=new Error(said||('HTTP '+r.status));
  err.status=r.status;
  err.serverSaid=said;
  err.deliberate=![502,503,504].includes(r.status);
  return err;
}

/* The sentence out of an error, without the word "Error:" in front of it.

   Every module ends its catch by printing `''+e`, which on an Error object is
   "Error: " and then the part worth reading. Now that a refusal arrives carrying
   the server's own explanation - which file, which line, what to change - that
   prefix is the only thing standing between the reader and it. */
const errText=e=>(e&&e.message)||String(e);

function apiFailed(e,u){
  const err=(e instanceof Error)?e:new Error(String(e));
  err.apiFailure=true;          // it was a request that failed, not the UI's code
  err.request=u;
  err.reachedServer=err.status!==undefined;   // a status means it answered
  return err;
}

/* ---------- the loading bar ----------
   "The menu is open but nothing is on it yet" used to look identical to "this is
   broken": the biggest mod takes a moment to read, and a blank panel says
   nothing about which of the two you are looking at.

   It counts REQUESTS rather than asking each module to report progress, which is
   why every module has one without a line of its own code: opened/closed are
   called by the API client above, the bar appears once a burst has lasted long
   enough to be worth mentioning, and the fraction is "answered / asked for so
   far". Traffic that isn't a load - the heartbeat, a progress poll, a settings
   save - is ignored, or the bar would blink every four seconds forever. */
const LOADBAR_IGNORE=[/\/api\/heartbeat/,/\/api\/bye/,/\/api\/progress/,/\/api\/settings$/];
const LOADBAR_DELAY=180;     // ms a burst must last before the bar is worth showing
const loadbar={
  open:0,done:0,label:'',timer:null,shown:false,
  ignored(u){return LOADBAR_IGNORE.some(re=>re.test(u));},
  opened(u,label){
    if(this.ignored(u))return;
    if(!this.open)this.done=0;                 // a new burst
    this.open++;
    if(label)this.label=label;
    if(!this.shown&&!this.timer)this.timer=setTimeout(()=>this.show(),LOADBAR_DELAY);
    this.paint();
  },
  closed(u){
    if(this.ignored(u))return;
    this.open=Math.max(0,this.open-1); this.done++;
    if(!this.open)this.hide(); else this.paint();
  },
  // What the bar SAYS. A module that knows better than "Loading…" passes a label
  // with its request; anything else keeps the last one until the burst ends.
  say(label){this.label=label;this.paint();},
  show(){this.timer=null;this.shown=true;
    const el=document.getElementById('loadbar'); if(el)el.classList.add('on');
    this.paint();},
  hide(){clearTimeout(this.timer);this.timer=null;this.shown=false;this.label='';
    const el=document.getElementById('loadbar'); if(el)el.classList.remove('on');},
  paint(){
    if(!this.shown)return;
    const el=document.getElementById('loadbar'); if(!el)return;
    const total=this.done+this.open;
    const pct=total?Math.round(100*this.done/total):0;
    // nothing to divide by yet -> sweep rather than sit at a made-up number
    el.classList.toggle('busy',total<2);
    if(total>=2)el.querySelector('.lbfill').style.width=Math.max(4,pct)+'%';
    el.querySelector('.lbtext').textContent=this.label||'Loading…';
    el.querySelector('.lbnum').textContent=total>1?`${this.done}/${total}`:'';
  }};
/* ---------- activity ----------
   What the PERSON did, into the same log as what the tool did.

   The log used to record every file written and nothing about the clicks that
   led there, so reading it back meant inferring intent from effects. These lines
   close that half: mode opened, mod picked, record opened, field changed from
   this to that, dialog closed with edits still pending.

   Batched, because a burst of clicking must not become a burst of requests: a
   flush goes out about once a second, and the queue is drained on the way out of
   the page too. */
const ACTIVITY_FLUSH=1200, ACTIVITY_MAX=60;
let _acts=[],_actT=null;
function activity(what,detail){
  _acts.push({what:what,detail:detail==null?'':''+detail});
  if(_acts.length>ACTIVITY_MAX)_acts.shift();
  if(!_actT)_actT=setTimeout(flushActivity,ACTIVITY_FLUSH);
}
function flushActivity(){
  clearTimeout(_actT); _actT=null;
  if(!_acts.length)return;
  const events=_acts; _acts=[];
  // fire and forget: the log is a record, never something the UI waits on
  try{fetch('/api/activity',{method:'POST',keepalive:true,
    headers:{'Content-Type':'application/json'},body:JSON.stringify({events})});}catch(e){}
}
// A field's OLD value is only knowable before it changes, so it is remembered on
// the way in. `change` rather than `input`: one line per value the user settled
// on, not one per keystroke.
const _actWas=new WeakMap();
document.addEventListener('focusin',e=>{
  const el=e.target;
  if(el&&/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName||''))_actWas.set(el,el.value);
},true);
// Controls that already write a better line of their own, so the generic one
// would only repeat them (and worse: a picker changed by code never saw the
// focusin, so its "was" would be blank).
const ACTIVITY_SKIP=['srcSel','dstSel','search'];
document.addEventListener('change',e=>{
  const el=e.target; if(!el||!el.tagName)return;
  if(ACTIVITY_SKIP.includes(el.id))return;
  const name=el.id||el.getAttribute('data-label')||el.getAttribute('data-row')
    ||el.getAttribute('data-bp')||el.name||el.className||el.tagName.toLowerCase();
  if(el.type==='checkbox'||el.type==='radio')
    return activity('ticked',`${name} -> ${el.checked?'on':'off'}`);
  const was=_actWas.get(el);
  if(was===el.value)return;
  // No focusin means nothing typed in this box - a picker set by code, or a
  // control drawn and changed in one go. Saying so beats printing an empty "was".
  activity('changed',was==null?`${name} -> “${(el.value||'').slice(0,120)}” (was not read)`
    :`${name}: “${was.slice(0,120)}” -> “${(el.value||'').slice(0,120)}”`);
  _actWas.set(el,el.value);
},true);
window.addEventListener('pagehide',flushActivity);

const esc=s=>(s==null?'':''+s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const q1=v=>v.replace(/'/g,"\\'");
// A note is a short lead line and then points. Prose that runs for six lines is
// unreadable in an 11.5px grey box, so anything carrying more than one fact is
// written this way. .count, .bnote, .sprnote and .gfdoc all style the list.
const docPoints=(lead,points)=>{const ps=points.filter(Boolean);
  return ps.length?lead+'<ul>'+ps.map(p=>'<li>'+p+'</li>').join('')+'</ul>':lead;};
function toast(m,ms=2800){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');clearTimeout(t._t);t._t=setTimeout(()=>t.classList.remove('show'),ms);}
// A faction has two names - the EDU's code ("teutonic_order") and the in-game one
// ("Clans of Enedwaith") - and which one you look for depends on what you are
// doing. Whichever is picked leads and sorts; the other rides along in brackets so
// the row is still readable either way.
const facBy=()=>(state.settings.faction_sort==='code'?'code':'name');
const facTwoNames=(code,name)=>!name?code
  :facBy()==='code'?`${code} (${name})`:`${name} (${code})`;
const facLabel=f=>facTwoNames(f,state.factionNames[f]);
// In a CHECKLIST the two names are split rather than run together: the one you
// are reading down the list for leads, and the other appears over the row on
// hover (.facrow .fc), so a long name is never cut short to make room for a code
// you only need to glance at once. Which one leads is the ⚙ faction_sort setting.
const facLead=(code,name)=>!name?code:(facBy()==='code'?code:name);
const facBehind=(code,name)=>!name?'':(facBy()==='code'?name:code);
// One checklist row: tick box, the leading name, and the hover-only detail.
function facCheckRow(code,name,onchange,checked,note,edited){
  const behind=[facBehind(code,name),note].filter(Boolean).join(' · ');
  return `<div class="facrow${edited?' edited':''}">
    <label class="chk"><input type="checkbox" ${checked?'checked':''} onchange="${onchange}">
      <span class="fn">${esc(facLead(code,name))}</span></label>
    ${behind||edited?`<span class="fc">${esc(behind)}${
      edited?(behind?' · ':'')+(checked?'added by you':'removed by you'):''}</span>`:''}</div>`;
}
const iconUrl=(mod,type,kind)=>`/icon?mod=${encodeURIComponent(mod)}&type=${encodeURIComponent(type)}&kind=${kind||'card'}`;
// Icon requests can be dropped when a page fires dozens at once (connection
// bursts). A missing icon returns a valid blank PNG (onload), so onerror only
// fires on a genuine connection failure - retry it a few times with backoff.
function iconRetry(img){
  const n=(+img.dataset.try||0)+1; img.dataset.try=n;
  if(n>4) return;                       // give up quietly after 4 tries
  const base=img.src.split('#')[0];
  setTimeout(()=>{img.src=base+'#r'+n;}, 120*n*n);
}

// Keep the server alive while this tab is open; tell it to stop when the tab closes
// (so a windowless server doesn't linger holding the port). A refresh sends 'bye'
// too, but the reloaded page resumes heartbeats within the server's grace window.
let _hbStarted=false;
function startHeartbeat(){
  if(_hbStarted)return; _hbStarted=true;
  const beat=()=>{try{fetch('/api/heartbeat',{method:'POST',keepalive:true});}catch(e){}};
  beat(); setInterval(beat,4000);
  const bye=()=>{try{navigator.sendBeacon('/api/bye');}catch(e){}};
  window.addEventListener('pagehide',bye);
  window.addEventListener('beforeunload',bye);
}
async function init(){
  try{
    startHeartbeat();
    const s=await api.get('/api/settings');state.settings=s;
    facSort.value=facBy();                 // remembered across runs like the rest
    restoreFilters();                      // …and so are the filters themselves
    // ?mod=&edit= - how "open this unit in a new tab" arrives. It picks the mod
    // and opens the editor for this tab only; the remembered mod is not changed.
    const qs=new URLSearchParams(location.search);
    const qMod=qs.get('mod'),qEdit=qs.get('edit');
    /* ?building=&lvl=&unit= - how the unit editor's Recruitment tab says "go and
       look at that building". The line opens at the tier the pool sits on and
       the unit's rows are flashed there, which is the whole point of the trip:
       a barracks trains sixty units and scrolling for the one you came for is
       the step the link exists to skip. `unit` is optional - without it this is
       just "open this building line". */
    const qBld=qs.get('building'),qLvl=qs.get('lvl'),qJump=qs.get('unit');
    // A launch lands on Home, whatever module you were in last time - that is
    // the point of having one. The remembered mode is not forgotten: Home offers
    // it as "last time you were in …", so it is a click rather than an ambush.
    state.mode=qEdit?'edit':qBld?'buildings':'home';
    await refreshMods(qMod||s.last_source,qMod||s.last_dest);
    wire(); applyMode(false);
    if(qEdit){
      if(state.data&&state.data.units.some(u=>u.type===qEdit))openEditor(qEdit);
      else toast(`“${qEdit}” is not a unit in ${state.src}`,4000);
    }
    else if(qBld){
      const lvl=parseInt(qLvl,10);
      await openBuilding(qBld,false,isFinite(lvl)?Math.max(0,lvl):undefined);
      // openBuilding gives up with a message of its own if the line is not there
      if(qJump&&state.bld&&state.bld.line===qBld)bldJumpPool(qJump);
    }
  }catch(e){
    // Every line of the startup is inside this try, so the catch used to blame
    // the server for anything that happened in any of them - including a plain
    // error in the UI's own code, which is exactly what a dropped <script>
    // looks like (the module's functions are not there, so the first call into
    // it throws). "Is the launcher still running?" is the wrong place to send
    // someone whose server answered every request in the same second, and the
    // log says it did. So each failure now says which one it was.
    console.error('startup failed', e);
    const why=esc(String((e&&e.message)||e));
    main.innerHTML=
      e&&e.apiFailure&&!e.reachedServer
      ? `<div class="empty">Couldn't reach the Medieval 2 GUI Toolkit server.<br>
        <span class="count">Is <code>Launch-Medieval2-GUI-Toolkit.bat</code> (python app.py) still running?</span><br><br>
        <button class="primary" onclick="init()">Retry</button></div>`
      : e&&e.apiFailure
      ? `<div class="empty">The server is running, but it answered with an error.<br>
        <span class="count">${why} from <code>${esc(e.request||'')}</code> - the reason is in <code>config\\server.log</code>.</span><br><br>
        <button class="primary" onclick="init()">Retry</button></div>`
      : `<div class="empty">The server is fine - the page is not.<br>
        <span class="count">${why}<br>A UI file that failed to download does exactly this, and a reload fetches it again. F12 → Console has the full trace.</span><br><br>
        <button class="primary" onclick="location.reload()">Reload</button>
        <button onclick="init()">Retry</button></div>`;
  }
}

const realMods=()=>state.mods.filter(m=>!m.pack);
async function refreshMods(pSrc,pDst){
  state.mods=await api.get('/api/mods');
  const opt=m=>`<option value="${esc(m.name)}">${esc(m.pack?'📦 '+m.name:m.name)}</option>`;
  srcSel.innerHTML=state.mods.map(opt).join('');
  // A mounted unit pack can only ever be a SOURCE: it holds a handful of units
  // and nothing else, and writing into it would go nowhere - it is deleted when
  // the pack is unmounted.
  dstSel.innerHTML=realMods().map(opt).join('');
  if(!state.mods.length){main.innerHTML='<div class="empty">No mods found. Click ⚙ Settings to point at your Medieval II folder.</div>';return;}
  const real=realMods().length?realMods():state.mods;
  state.src=pSrc&&state.mods.some(m=>m.name===pSrc)?pSrc:real[0].name;
  state.dst=pDst&&real.some(m=>m.name===pDst)?pDst:(real[1]?.name||real[0].name);
  // Older builds persisted a single-mod mode's mirrored destination as
  // last_dest, so a remembered pair can arrive as A -> A. Starting Transfer
  // pointed at the source mod reads as "copy this onto itself" - pick a real
  // second mod instead, exactly as a first run would.
  if(state.mode==='transfer'&&state.dst===state.src&&real.length>1)
    state.dst=real.find(m=>m.name!==state.src).name;
  state.xferDst=state.dst;
  srcSel.value=state.src; dstSel.value=state.dst;
  state.destData=null;
  await loadSource();
}
/* What the unit list says when the mod behind it could not be read.

   Two places paint it and they must not disagree: the load's own catch, and
   render() - which runs again on every mode switch, and had only "Loading…" to
   put there. That is what the person in the log was left looking at: the reason
   was drawn for a moment, then a screen that said the tool was still reading a
   mod nothing was being read for, under a header that had already given up. */
const unitListFailedHtml=(mod,why)=>`<div class="empty">Couldn't load “${esc(mod)}”.<br>
  <span class="count">${esc(why)}</span><br><br>
  <button class="primary" onclick="loadSource()">Retry</button></div>`;

// The unit list is what Transfer and Edit show; the other modes have their own
// workspace, so this must not paint over one of those just because the units
// finished loading underneath it.
const unitListMode=()=>state.mode==='transfer'||state.mode==='edit';
async function loadSource(){
  const mod=state.src;
  // Every load ABANDONS the one before it. Without this, picking a second mod
  // while the first was still being read left both requests running: the older
  // one held one of the browser's handful of connections to the end, and if it
  // was the one that finished last, its units were the ones you were left
  // looking at. Switching mods is the commonest thing anyone does here.
  const {gen,signal}=newLoad();
  activity('reading mod',mod);
  state.loadError=null;
  if(unitListMode())main.innerHTML='<div class="empty">Loading '+esc(mod)+'…</div>';
  let r;
  try{
    r=await api.get('/api/units?mod='+encodeURIComponent(mod),
                    {signal,label:`Reading ${mod}’s units…`});
  }catch(e){
    if(isAborted(e)||loadStale(gen)||mod!==state.src)return;   // a later load owns the screen
    state.loadError={mod,why:String((e&&e.message)||e)};
    if(unitListMode())main.innerHTML=unitListFailedHtml(mod,state.loadError.why);
    return;
  }
  if(loadStale(gen)||mod!==state.src)return;   // a later load owns the screen now
  state.data=r;
  state.factionNames=state.data.faction_names||{};
  // Keep whatever is ticked. Saving a unit or finishing a transfer reloads this
  // list, and re-ticking the same filters every time was maddening. Only values
  // this mod doesn't have are dropped - a filter that can never match would hide
  // everything with no visible reason why.
  let dropped=false;
  const prune=(key,values)=>{const ok=new Set(values||[]);
    for(const v of [...state.sel[key]])if(!ok.has(v)){state.sel[key].delete(v);dropped=true;}};
  prune('faction',state.data.factions);
  prune('category',state.data.categories);
  prune('class',state.data.classes);
  if(dropped)saveFilters();   // don't let the next run resurrect what was dropped
  // same for a pending multi-selection: a unit that was just deleted (or that
  // this mod never had) can't be transferred, so it can't stay ticked
  const types=new Set(state.data.units.map(u=>u.type));
  for(const t of [...state.selected])if(!types.has(t))state.selected.delete(t);
  updateBatchBtn();
  buildFilter('factionFilter',state.data.factions,'faction',true);
  buildFilter('categoryFilter',state.data.categories,'category');
  buildFilter('classFilter',state.data.classes,'class');
  syncEraBoxes();
  render();
}
/* ---------- filters remembered ----------
   The filter panel is "where I was looking", the same kind of state as the mod
   pair and the faction sort, so it is persisted the same way and restored on
   the next run instead of only surviving until the next reload. */
function restoreFilters(){
  const f=state.settings.filters||{};
  state.sel={faction:new Set(f.faction||[]),category:new Set(f.category||[]),
             class:new Set(f.class||[]),era:new Set(f.era||[])};
  if(f.group_by)groupBy.value=f.group_by;
  mercOnly.checked=!!f.merc_only;
  state.folded=new Set(state.settings.folded_groups||[]);
  syncEraBoxes();
}
function syncEraBoxes(){document.querySelectorAll('.era').forEach(cb=>cb.checked=state.sel.era.has(cb.value));}
let _saveFiltersT=null;
function saveFilters(){                       // debounced: ticking is a burst
  clearTimeout(_saveFiltersT);
  _saveFiltersT=setTimeout(()=>{
    state.settings.filters={faction:[...state.sel.faction],category:[...state.sel.category],
      class:[...state.sel.class],era:[...state.sel.era],
      group_by:groupBy.value,merc_only:mercOnly.checked};
    api.post('/api/settings',{filters:state.settings.filters});
  },400);
}
function filtersChanged(){saveFilters();render();}
async function ensureDest(){ if(!state.destData||state.destData.mod!==state.dst){state.destData=await api.get('/api/units?mod='+encodeURIComponent(state.dst));} return state.destData; }

/* ---------- the filter sidebar folds ----------
   Every mode's sidebar is a run of <h3> headings with that group's controls
   under each one, and on a mod with sixty factions the first heading is the only
   one you can see without scrolling. So each heading becomes the control that
   folds its own group, exactly as the group headers in the unit grid already do
   (see toggleGroup), and which ones are shut is remembered across runs like the
   rest of the panel.

   The grouping is read off the markup rather than written into it: a heading
   owns every element after it up to the next heading. That means a sidebar can
   gain a group without anyone remembering to wrap it, and it is why one function
   covers the unit sidebar and the buildings sidebar alike.

   `.fgn` carries "3" when a group has something ticked, so a filter that is
   hiding rows can never be folded out of sight without saying so. */
function wireFilterFolds(){
  document.querySelectorAll('aside.filters').forEach(aside=>{
    if(aside.dataset.folds)return;                 // already wrapped
    aside.dataset.folds='1';
    const kids=[...aside.children];
    let head=null,run=[];
    const close=()=>{
      if(!head)return;
      const body=document.createElement('div');
      body.className='fgbody';
      head.after(body);
      run.forEach(el=>body.appendChild(el));
      const key=aside.id+':'+head.textContent.trim();
      head.classList.add('filtfold');
      head.dataset.fg=key;
      head.innerHTML=`<span class="fgc">▶</span><span class="fgt">${
        esc(head.textContent.trim())}</span><span class="fgn"></span>`;
      head.onclick=()=>toggleFilterFold(key);
      run=[];
    };
    kids.forEach(el=>{
      if(el.tagName==='H3'){close(); head=el;}
      else if(head)run.push(el);
    });
    close();
  });
  paintFilterFolds();
}
const filterFolded=()=>(state.settings.filters_folded||[]);
function toggleFilterFold(key){
  const shut=new Set(filterFolded());
  if(shut.has(key))shut.delete(key); else shut.add(key);
  state.settings.filters_folded=[...shut];
  api.post('/api/settings',{filters_folded:state.settings.filters_folded});
  paintFilterFolds();
}
// How many boxes a group has ticked, so a folded group still owns up to filtering.
function filterFoldCount(body){
  return body.querySelectorAll('input[type=checkbox]:checked').length;
}
function paintFilterFolds(){
  const shut=new Set(filterFolded());
  document.querySelectorAll('aside.filters h3.filtfold').forEach(h=>{
    const body=h.nextElementSibling;
    if(!body||!body.classList.contains('fgbody'))return;
    const off=shut.has(h.dataset.fg);
    h.classList.toggle('shut',off);
    body.classList.toggle('shut',off);
    const n=filterFoldCount(body);
    const tag=h.querySelector('.fgn');
    if(tag)tag.textContent=n?String(n):'';
    h.title=off?'Click to open this group.':'Click to fold this group shut.';
  });
}
function buildFilter(id,values,key,useLabel){
  const box=document.getElementById(id);
  // factions are listed under whichever name is leading, so the A→Z the user
  // picked is the A→Z they see here as well as in the group headers
  const list=useLabel?[...(values||[])].sort((a,b)=>facLabel(a).localeCompare(facLabel(b)))
                     :(values||[]);
  box.innerHTML=list.map(v=>`<label class="opt"><input type="checkbox" value="${esc(v)}" ${
    state.sel[key].has(v)?'checked':''}>${esc(useLabel?facLabel(v):v)}</label>`).join('')
    ||'<span class="count">None</span>';
  box.querySelectorAll('input').forEach(cb=>cb.onchange=()=>{const s=state.sel[key];cb.checked?s.add(cb.value):s.delete(cb.value);filtersChanged();paintFilterFolds();});
  paintFilterFolds();
}
/* ---------- burger menu ----------
   The single registry of modules. Everything the menu shows - and the header
   label, and the per-mode document title - comes from here, so a new module is
   one entry in this array plus its render function. */
// `sub:true` = still a real mode, but reached through a tab strip inside its
// host rather than from this menu (Sprites lives in the BMDB editor; Traits,
// Ancillaries, Factions and Strings live in Minor Files).
const MODES=[
  {id:'home',     icon:'⌂', name:'Home',          hint:'Your mods, and what each one is ready for'},
  {id:'edit',     icon:'✎', name:'Unit Editor',   hint:'Change, clone or delete one mod’s units'},
  {id:'transfer', icon:'⚔', name:'Unit Transfer', hint:'Copy a unit from one mod into another'},
  {id:'buildings',icon:'🏰', name:'Buildings',     hint:'Browse and edit export_descr_buildings'},
  {id:'campmap',  icon:'🌍', name:'Campaign Map',  hint:'The ten map layers, the regions painted on them and what the game reads'},
  {id:'bmdb',     icon:'🗄', name:'BMDB + Sprites Editor', hint:'What battle_models.modeldb names, and the sprites it points at'},
  {id:'sounds',   icon:'🔊', name:'Unit Sounds',   hint:'Pick which voice entry each unit speaks with'},
  {id:'minor',    icon:'🗺', name:'Minor Files',   hint:'Rebels, religions, cultures, traits, factions and text'},
  {id:'sprites',  icon:'🖼', name:'Sprites',       sub:true, hint:'Generate and wire the far-LOD unit sprites'},
  {id:'stratmap', icon:'🗺', name:'Strat map models', sub:true, hint:'What descr_model_strat.txt names, and what the campaign map never draws'},
  {id:'cards',    icon:'🖼', name:'Unit & info cards', sub:true, hint:'The two pictures per unit, deduplicated into the merc folder'},
  {id:'traits',   icon:'🎖', name:'Traits',        sub:true, hint:'Character traits, their levels and the triggers that give them'},
  {id:'ancillaries',icon:'🏅', name:'Ancillaries',  sub:true, hint:'The items and followers a character picks up'},
  {id:'factions', icon:'🛡', name:'Factions',      sub:true, hint:'Each faction’s culture, religion, colours and horde'},
  {id:'strings',  icon:'🔤', name:'Strings',       sub:true, hint:'The compiled text files the game actually reads'},
];
const modeDef=id=>MODES.find(m=>m.id===id)||MODES[0];

/* ---------- the Minor Files tab strip ----------
   Nine campaign files behind one strip. Five are shapes of one parser and are
   tabs of the `minor` mode; the other four are big enough to have their own
   mode, so their tab switches mode rather than tab. Everything the strip needs
   is here because five different files draw it. */
const MINOR_TABS=[
  {id:'rebels',      label:'Rebel factions'},
  {id:'religions',   label:'Religions'},
  {id:'resources',   label:'Resources'},
  {id:'cultures',    label:'Cultures'},
  {id:'names',       label:'Character names'},
  {mode:'traits',      label:'Traits'},
  {mode:'ancillaries', label:'Ancillaries'},
  // 17f: a faction is two files - what it IS (descr_sm_factions.txt) and what
  // it starts the campaign WITH (descr_strat.txt) - and they are one screen
  // now, inside the Campaign Map. This tab still lands somewhere, and where it
  // lands depends on whether the mod has a map at all: with one, the combined
  // screen; without one, the old mode, which is the only place that mod's
  // factions can be edited.
  {mode:'factions', label:'Factions', go:'minorFactions()'},
  {mode:'strings',     label:'Strings'},
];
let minorWantTab=null;
function minorTabsHtml(active,note){
  return `<div class="mftabs">${MINOR_TABS.map(t=>{
    const on=t.mode?state.mode===t.mode:(state.mode==='minor'&&active===t.id);
    const go=t.go?t.go:t.mode?`minorGo(null,'${t.mode}')`:`minorGo('${t.id}')`;
    return `<button class="mftab${on?' on':''}" onclick="${go}">${esc(t.label)}</button>`;
  }).join('')}${note?`<span class="count" style="margin-left:auto">${esc(note)}</span>`:''}</div>`;
}
function minorGo(tab,mode){
  if(mode)return setAppMode(mode);
  if(state.mode==='minor')return mfTab(tab);
  minorWantTab=tab; state.mf=null; setAppMode('minor');
}

/* Where the Factions tab goes now (17f).

   To the combined screen when this mod has a campaign map to put it on, and to
   the old mode when it has not - a mod that ships units and lets the game's own
   map stand is the ordinary case, and it still has factions to edit. The map's
   readiness is the same one Home shows, so the two never disagree. */
function minorFactions(){
  campmapWantFactions=true;
  setAppMode('campmap');
}
//: Set by the tab above and read once by the campaign map: it opens the faction
//: screen when it has drawn, and hands the mode back to `factions` when this
//: mod has no map to draw at all.
let campmapWantFactions=false;

/* ---------- the findings banner ----------
   "14 things to look at - the marked rows below" was the whole message, so the
   only way to learn WHAT was to open every marked row. It now opens: one line
   per finding, each a link to the record it is about. Shared by Traits,
   Ancillaries, Factions and Minor Files, which all produce the same shape.

   `open` is remembered per screen in `state.findOpen`, so opening it does not
   close again on the next repaint. */
state.findOpen={};
function findingsHtml(key,list,onopen){
  const n=(list||[]).length;
  if(!n)return '';
  const open=!!state.findOpen[key];
  const rows=(list||[]).map(f=>`<div class="findrow">
      ${f.name?`<a class="ulink" onclick="${onopen}('${q1(esc(f.name))}')"
        >${esc(f.name)}</a> `:''}<span>${esc(f.message||f.kind||'')}</span>
    </div>`).join('');
  return `<div class="trnote w-warn">
    <button class="findtog" onclick="findingsToggle('${q1(esc(key))}')">
      ${open?'▾':'▸'} ${n} thing${n===1?'':'s'} to look at</button>
    ${open?`<div class="findlist">${rows}</div>`
          :'<div class="count">The marked rows below, or open this to read them.</div>'}
  </div>`;
}
function findingsToggle(key){state.findOpen[key]=!state.findOpen[key]; render();}

/* ---------- the draggable divider between a list and its 3D column ----------
   Two screens dock the model viewer beside something else - the unit editor
   beside its fields, BMDB mode beside its entry list - and both used to give it
   a width decided here and no way to change it. Full screen was the only way to
   see a model bigger, and full screen takes the thing you were reading with it.

   So the column gets a grab bar. One implementation for both, because the two
   splits differ in nothing but which element and which saved key: the panel is
   always the LAST child, the bar goes immediately before it, and the drag moves
   the boundary rather than either side, so the list simply takes what is left.

   The width is per-screen and persisted (`/api/settings`), because the answer to
   "how much room should the model get" depends on what you are doing and not on
   which dialog you last opened. Double-click puts back the default. */
const SPLIT_MIN_PANEL = 240;    // narrower than this and the viewer's own bar wraps
const SPLIT_MIN_MAIN  = 320;    // narrower than this and the list beside it is unreadable

/* The width to open at: what was saved, else the screen's own default, clamped
   so neither side can be squeezed out of existence by a window that has since
   been made narrower. `fallback` may be a number or a function of the space. */
function splitWidth(split, key, fallback){
  const avail = split.clientWidth || 0;
  const saved = +(state.settings && state.settings[key]) || 0;
  const want = saved > 0 ? saved
             : (typeof fallback === 'function' ? fallback(avail) : fallback);
  if(!avail) return want;
  return Math.max(SPLIT_MIN_PANEL, Math.min(want, Math.max(SPLIT_MIN_PANEL, avail - SPLIT_MIN_MAIN)));
}

/* Size the panel and put a working grab bar in front of it.

   Called from the same place the panel is appended, every render - the pages
   these live on rebuild their HTML wholesale (a keystroke in the BMDB search
   box does), so the bar is a fresh element each time while the panel itself is
   the detached-and-reattached live canvas. */
function splitInstall(split, panel, key, fallback){
  if(!split || !panel) return;
  panel.style.flex = '0 0 ' + Math.round(splitWidth(split, key, fallback)) + 'px';
  let bar = split.querySelector(':scope > .splitbar');
  if(!bar){
    bar = document.createElement('div');
    bar.className = 'splitbar';
    bar.title = 'Drag to resize the 3D panel · double-click for the default width';
  }
  split.insertBefore(bar, panel);
  bar.onpointerdown = ev => {
    // Left button only, and never let the drag select the list behind it.
    if(ev.button) return;
    ev.preventDefault();
    const startX = ev.clientX, startW = panel.getBoundingClientRect().width;
    const room = split.clientWidth;
    try{ bar.setPointerCapture(ev.pointerId); }catch(e){}
    bar.classList.add('drag');
    document.body.classList.add('splitting');
    // The panel is on the RIGHT, so dragging left (a falling clientX) makes it
    // wider. The viewer's canvas re-reads its own clientWidth every frame, so
    // nothing has to be told the size changed.
    const move = e => {
      const w = Math.max(SPLIT_MIN_PANEL,
                Math.min(startW + (startX - e.clientX),
                         Math.max(SPLIT_MIN_PANEL, room - SPLIT_MIN_MAIN)));
      panel.style.flex = '0 0 ' + Math.round(w) + 'px';
    };
    const up = () => {
      bar.removeEventListener('pointermove', move);
      bar.removeEventListener('pointerup', up);
      bar.removeEventListener('pointercancel', up);
      bar.classList.remove('drag');
      document.body.classList.remove('splitting');
      splitSave(key, Math.round(panel.getBoundingClientRect().width));
    };
    bar.addEventListener('pointermove', move);
    bar.addEventListener('pointerup', up);
    bar.addEventListener('pointercancel', up);
  };
  bar.ondblclick = () => {
    const w = Math.round(splitWidth(split, '', fallback));
    panel.style.flex = '0 0 ' + w + 'px';
    splitSave(key, w);
  };
}
function splitSave(key, px){
  if(!key || !(px > 0)) return;
  state.settings[key] = px;
  api.post('/api/settings', {[key]: px});
}

/* ---------- panes the user can resize ----------

   Every list in this tool sits in a box whose height someone chose once: 340px
   for a building's recruitment pools, 230px for a unit's upgrade list, 92vh for
   the dialog holding either. Those are fine defaults and wrong for half the
   work. A barracks that trains sixty units gets the same 340px as one that
   trains two, on a monitor the tool never asked about, and the only ways out
   were scrolling a list inside a scrolling dialog or not looking.

   So every scroll box on the page grows a grab corner, and so do the dialog and
   the unit drawer. Three decisions keep that one small piece of code instead of
   fifty scattered ones:

     * **the boxes find themselves.** A scroll box in this stylesheet is a rule
       that sets `max-height` and `overflow:auto` together, and there is no
       second kind of one. `rszSelectors` reads the page's own CSS once at
       startup and collects those selectors, so a list written next month is
       resizable the day it is written, with nothing to remember here.
     * **the browser does the dragging.** `resize` is a real CSS property with a
       real grip and real hit-testing. Two things stop it working out of the
       box: a `max-height` caps the drag, and these screens rebuild their markup
       wholesale so the result is thrown away on the next keystroke. Undoing
       those two is the whole job.
     * **nothing is touched until it is dragged.** A box keeps the height the
       stylesheet gave it, shrink-to-fit and all, until the pointer goes down on
       its corner. Only then does it get a pinned height, so a screen nobody has
       resized still lays out exactly as it always did.

   Sizes are remembered per box, in `pane_sizes` on `/api/settings`, because how
   tall the recruitment list should be is a fact about the user's screen and
   habits rather than about the dialog that happens to be open. Double-click a
   grip to hand the box back to the stylesheet. */

//: Nothing may be dragged smaller than this: a box with no room for a row is a
//: box that looks broken rather than small.
const RSZ_MIN=64;
//: The browser's grip is a small square in the bottom-right corner. This is how
//: far in from that corner a press still counts as aiming at it.
const RSZ_GRIP=20;
/* Boxes this sweep must NOT claim. A `.wpop` is a menu that opens under a
   button and closes on the next click, so a height remembered for it would
   outlive the thing it was measured on. `.modal` passes the same test the sweep
   looks for and is deliberately left to `rszModal`, which sizes it in both
   directions rather than one. */
const RSZ_SKIP=/\.wpop\b|^\.modal\b/;

//: Built once by `rszInit`, from the stylesheet. Empty until then.
let rszSel='';
//: The box the pointer went down on, waiting for the release that sizes it.
let rszDragging=null;
let rszSaveTimer=0;

/* Every selector in the page's own CSS that describes a scroll box.

   Reading `document.styleSheets` rather than keeping a list here is what makes
   this maintenance-free, and it is safe to do: the toolkit's CSS is a `<style>`
   block in index.html, same origin as the page, so `cssRules` is readable. A
   sheet that refuses is skipped rather than fatal. */
function rszSelectors(){
  const out=[];
  for(const sheet of document.styleSheets){
    let rules=null;
    try{ rules=sheet.cssRules; }catch(e){ continue; }   // a cross-origin sheet gives none
    for(const rule of rules||[]){
      const st=rule.style;
      if(!st||!rule.selectorText)continue;
      // `overflow:auto` and `overflow-y:auto` are the same intent written two ways
      const ov=st.overflow||st.overflowY;
      if(!st.maxHeight||!/^(auto|scroll)$/.test(ov||''))continue;
      if(RSZ_SKIP.test(rule.selectorText))continue;
      out.push(rule.selectorText);
    }
  }
  return out.join(',');
}

//: The saved sizes, as a live object on `state.settings` so a write is seen by
//: the next read without a round trip.
function rszSizes(){
  const s=state.settings||(state.settings={});
  if(!s.pane_sizes||typeof s.pane_sizes!=='object')s.pane_sizes={};
  return s.pane_sizes;
}

/* What a box is called in the saved sizes. Its `id` when it has one: the
   recruitment list is `#bldPools` in both its row and its grid form, and one
   remembered height for "the recruitment list" is the right answer either way.
   Failing that, its classes, which is where the height came from to begin with. */
function rszKey(el){
  if(el.id)return el.id;
  const c=(el.getAttribute('class')||'').trim().replace(/\s+/g,'.');
  return c?'.'+c:'';
}

//: Save, coalesced: a drag ends once but several boxes can be sized in a burst,
//: and settings.json is rewritten whole either way.
function rszSave(){
  const map=rszSizes();
  clearTimeout(rszSaveTimer);
  rszSaveTimer=setTimeout(()=>{
    try{ api.post('/api/settings',{pane_sizes:map}); }catch(e){}
  },400);
}

/* Give a box an explicit height, which means taking the stylesheet's ceiling off
   first: `max-height` outranks `height`, so leaving it in place is why dragging
   a 340px list downwards used to do nothing at all. The ceiling is remembered on
   the element so a double-click has something to put back. */
function rszPin(el,px){
  if(el.dataset.rszDef===undefined){
    const d=parseFloat(getComputedStyle(el).maxHeight);
    el.dataset.rszDef=(d>0?Math.round(d):'');
  }
  el.style.maxHeight='none';
  el.style.height=Math.max(RSZ_MIN,Math.round(px))+'px';
}

//: Hand a box back to the stylesheet, and forget it was ever dragged.
function rszReset(el){
  el.style.height=''; el.style.maxHeight=''; el.style.width=''; el.style.maxWidth='';
  delete rszSizes()[rszKey(el)];
  rszSave();
}

/* Turn the grip on for every scroll box under `root`, and put back the height
   any of them was last dragged to.

   `dataset.rszOn` is per ELEMENT, not per key: these screens replace their
   markup rather than update it, so the box here now is a different object from
   the one that was here a frame ago and has to be set up again. That is also
   what makes the flag a cheap enough guard to run on every mutation. */
function rszApply(root){
  if(!rszSel)return;
  let els;
  try{ els=(root||document).querySelectorAll(rszSel); }catch(e){ return; }
  const map=rszSizes();
  els.forEach(el=>{
    if(el.dataset.rszOn)return;
    el.dataset.rszOn='1';
    el.style.resize='vertical';
    /* No `title` here on purpose: one on every list means a tooltip trailing the
       pointer across a screen made of lists. The corner is drawn to be seen
       instead, by `::-webkit-resizer` in index.html. */
    const saved=map[rszKey(el)];
    if(saved>0)rszPin(el,saved);
  });
}

/* The dialog itself, which is one element reused by every screen that opens one
   (`#modal`, put back to a bare `class="modal"` by `closeModal`). So its size is
   remembered against the class it is wearing: the wide editor dialog and the
   narrow confirm boxes are different windows to everyone except the DOM.

   Width as well as height here, because a dialog is the one box whose left edge
   is not pinned to something the user already chose. */
function rszModal(){
  const m=document.getElementById('modal');
  if(!m)return;
  const key='dlg:'+(m.getAttribute('class')||'modal').trim().replace(/\s+/g,'.');
  if(m.dataset.rszKey===key)return;      // the same dialog repainting, not a new one
  m.dataset.rszKey=key;
  m.style.resize='both';
  m.style.width=''; m.style.height=''; m.style.maxWidth=''; m.style.maxHeight='';
  const s=rszSizes()[key];
  if(!s||!(s.w>0)||!(s.h>0))return;
  // A size saved on a bigger monitor must not open a dialog wider than the
  // window it is centred in, so both are clamped to what there is now.
  m.style.maxWidth='none'; m.style.maxHeight='none';
  m.style.width=Math.max(320,Math.min(s.w,window.innerWidth-24))+'px';
  m.style.height=Math.max(160,Math.min(s.h,window.innerHeight-24))+'px';
}

/* The unit drawer slides in from the right and stays pinned there, so the
   browser's own grip is no use: it sits in the bottom-right corner and drags the
   panel off the screen. This one is a bar down the drawer's LEFT edge, worked
   the way the 3D splitter above is, and it is the only hand-rolled resizer
   here. */
const RSZ_DRAWER_MIN=280;
function rszDrawer(){
  const d=document.getElementById('drawer');
  if(!d)return;
  if(!d.dataset.rszOn){
    d.dataset.rszOn='1';
    const saved=rszSizes()['drawer'];
    if(saved>0)d.style.width=Math.max(RSZ_DRAWER_MIN,Math.min(saved,window.innerWidth-40))+'px';
  }
  // The drawer is repainted by assigning its innerHTML, which takes the bar with
  // it. Asking whether the bar is there beats remembering that it once was.
  if(d.querySelector(':scope > .drawergrip'))return;
  const bar=document.createElement('div');
  bar.className='drawergrip';
  bar.title='Drag to resize this panel · double-click for the default width';
  // First child, not last: the bar floats beside the content rather than under
  // the end of it, and a drawer scrolled to the bottom still has one.
  d.insertBefore(bar,d.firstChild);
  bar.onpointerdown=ev=>{
    if(ev.button)return;
    ev.preventDefault();
    const startX=ev.clientX,startW=d.getBoundingClientRect().width;
    try{ bar.setPointerCapture(ev.pointerId); }catch(e){}
    document.body.classList.add('splitting');
    // The drawer's right edge is fixed, so dragging LEFT is what widens it.
    const move=e=>{
      d.style.width=Math.round(Math.max(RSZ_DRAWER_MIN,
        Math.min(startW+(startX-e.clientX),window.innerWidth-40)))+'px';
    };
    const up=()=>{
      bar.removeEventListener('pointermove',move);
      bar.removeEventListener('pointerup',up);
      bar.removeEventListener('pointercancel',up);
      document.body.classList.remove('splitting');
      rszSizes()['drawer']=Math.round(d.getBoundingClientRect().width);
      rszSave();
    };
    bar.addEventListener('pointermove',move);
    bar.addEventListener('pointerup',up);
    bar.addEventListener('pointercancel',up);
  };
  bar.ondblclick=()=>{ d.style.width=''; delete rszSizes()['drawer']; rszSave(); };
}

/* Was this press aimed at the browser's grip? The grip is painted by the box
   itself and hit-tested ahead of its own contents, exactly like a scrollbar, so
   a press on it names the BOX as its target even when a child is sitting under
   the corner. That is what tells a grab from a click on the last row. */
function rszAtGrip(el,ev){
  if(ev.target!==el)return false;
  const r=el.getBoundingClientRect();
  return ev.clientX>=r.right-RSZ_GRIP&&ev.clientY>=r.bottom-RSZ_GRIP;
}

//: The scroll box or dialog a press landed on the grip of, or null.
function rszTarget(ev){
  const t=ev.target;
  if(!t||!t.closest)return null;
  const el=t.closest(rszSel?rszSel+',.modal':'.modal');
  return el&&rszAtGrip(el,ev)?el:null;
}

function rszInit(){
  rszSel=rszSelectors();
  const paint=()=>{ rszApply(document.body); rszModal(); rszDrawer(); };

  /* One observer for the whole page rather than a call at the end of thirty
     render functions. Every screen here rebuilds by assigning `innerHTML`, so
     "a box appeared" is exactly a childList mutation, and folding a burst of
     them into one frame keeps the cost at a single query per repaint. */
  let queued=false;
  const bump=recs=>{
    let worth=false;
    for(const r of recs){
      if(r.type==='attributes'){ if(r.target.id==='modal')worth=true; }
      else if(r.addedNodes.length)worth=true;
      if(worth)break;
    }
    if(!worth||queued)return;
    queued=true;
    /* A timeout rather than `requestAnimationFrame`, which is the obvious choice
       and the wrong one: a window the OS considers occluded gets no frames at
       all, so a dialog opened behind another window came up with none of its
       boxes wired and stayed that way until something forced a repaint. This
       work is a query and a few style writes, not drawing, so it does not need
       to be in a frame to be right. */
    setTimeout(()=>{ queued=false; paint(); },0);
  };
  new MutationObserver(bump).observe(document.body,
    {childList:true,subtree:true,attributes:true,attributeFilter:['class']});

  /* The press has to pin the height BEFORE the browser starts its drag, or the
     `max-height` the box still carries caps that first drag and only the second
     one appears to work. Capture phase on mousedown is the last moment that is
     still true. */
  document.addEventListener('mousedown',ev=>{
    if(ev.button)return;
    const el=rszTarget(ev);
    if(!el)return;
    const r=el.getBoundingClientRect();
    if(el.id==='modal'){
      el.style.maxWidth='none'; el.style.maxHeight='none';
      el.style.width=Math.round(r.width)+'px';
      el.style.height=Math.round(r.height)+'px';
    }else rszPin(el,r.height);
    rszDragging=el;
  },true);

  document.addEventListener('mouseup',()=>{
    const el=rszDragging; rszDragging=null;
    if(!el)return;
    const r=el.getBoundingClientRect();
    if(el.id==='modal')rszSizes()[el.dataset.rszKey||'dlg:modal']=
      {w:Math.round(r.width),h:Math.round(r.height)};
    else rszSizes()[rszKey(el)]=Math.round(r.height);
    rszSave();
  },true);

  //: Double-click the grip for the size the stylesheet meant.
  document.addEventListener('dblclick',ev=>{
    const el=rszTarget(ev);
    if(!el)return;
    ev.preventDefault();
    if(el.id==='modal'){
      el.style.width=''; el.style.height=''; el.style.maxWidth=''; el.style.maxHeight='';
      delete rszSizes()[el.dataset.rszKey||'dlg:modal'];
      rszSave();
    }else rszReset(el);
  },true);

  paint();
}

/* Which cleanup dialog the toolbar's 🧹 button opens. One lookup rather than a
   chain of ifs at the click site, because every tab of BMDB mode that grows a
   cleaner adds a row here and nothing else. */
const cleanupFor=mode=>({bmdb:openCleanup, stratmap:openStratCleanup}[mode]
  || (()=>toast('Nothing to clean up on this tab.')));

/* ---------- the BMDB tab strip ----------
   Sprites are the far-LOD half of a modeldb entry, so they are a tab of the
   BMDB editor rather than a module of their own. */
const BMDB_TABS=[{mode:'bmdb',label:'Model entries'},{mode:'sprites',label:'Sprites'},
  {mode:'stratmap',label:'Strat map'},{mode:'cards',label:'Unit cards'}];
const bmdbTabsHtml=note=>`<div class="mftabs">${BMDB_TABS.map(t=>
  `<button class="mftab${state.mode===t.mode?' on':''}" onclick="setAppMode('${t.mode}')"
    >${esc(t.label)}</button>`).join('')}${
  note?`<span class="count" style="margin-left:auto">${esc(note)}</span>`:''}</div>`;
function navOpen(open){
  navMenu.classList.toggle('open',open);
  navBack.classList.toggle('open',open);
  navMenu.setAttribute('aria-hidden',open?'false':'true');
}
// NB: not "setMode" - the composer already owns that name (its new/base/replace
// switch), and function declarations hoist, so the later one would silently win.
// `returning` is the Back button coming the other way: the trail is being
// walked out of, so nothing new goes onto it.
function setAppMode(id,returning){
  navOpen(false);
  if(id===state.mode)return;
  if(!returning){
    state.modeTrail.push(state.mode);
    // A session wanders - twenty-four steps back is already further than anyone
    // presses, and the oldest of them are not worth carrying.
    if(state.modeTrail.length>24)state.modeTrail.shift();
  }
  activity('opened',`${modeDef(id).name} (mod: ${state.src||'none'})`);
  state.mode=id;applyMode(true);
}
// keeps the header label and the menu's highlighted row honest - called from
// applyMode so every way of switching (menu, pack mount, building hop) lands here
// A sub-mode has no row of its own in the menu, so its HOST row lights up.
const MODE_HOST={sprites:'bmdb',stratmap:'bmdb',cards:'bmdb',traits:'minor',
  ancillaries:'minor',factions:'minor',strings:'minor'};
function syncNav(){
  const d=modeDef(state.mode), host=MODE_HOST[state.mode]||state.mode;
  navCur.textContent=d.icon+' '+d.name;
  document.querySelectorAll('#navModes .navitem').forEach(b=>
    b.classList.toggle('on',b.dataset.mode===host));
}
function wire(){
  wireFilterFolds();
  navModes.innerHTML=MODES.filter(m=>!m.sub).map(m=>`<button class="navitem" data-mode="${m.id}">
      <span class="ic">${m.icon}</span>
      <span><span class="nm">${esc(m.name)}</span><span class="hint">${esc(m.hint)}</span></span>
    </button>`).join('');
  navModes.querySelectorAll('.navitem').forEach(b=>b.onclick=()=>setAppMode(b.dataset.mode));
  navBtn.onclick=()=>navOpen(!navMenu.classList.contains('open'));
  navBack.onclick=()=>navOpen(false);
  creditsBtn.onclick=()=>{navOpen(false);openCredits();};
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&navMenu.classList.contains('open'))navOpen(false);});
  newUnitBtn.onclick=openNewUnitPicker;
  tidyEduBtn.onclick=openEduTidy;
  // Picking the mod that's already on the other side swaps the pair rather than
  // leaving a pointless A -> A: with A -> B, choosing A as the dest gives B -> A.
  srcSel.onchange=async e=>{
    const v=e.target.value;
    if(v!==state.src)
      activity('picked mod',`${state.mode==='transfer'?'source: ':''}${v} (was ${state.src})`);
    // A ticked pile belongs to the mod it was ticked in - carrying it to another
    // mod would transfer whatever happens to share a type name over there.
    if(v!==state.src)clearSelection();
    // Edit / bmdb mode works on a single mod, so both sides follow the picker.
    if(state.mode!=='transfer'){state.src=state.dst=v;dstSel.value=v;state.destData=null;
      state.cfg={};state.bmdb=null;state.snd=null;state.destSnd=null;state.str=null;
      state.tr=null;state.an=null;state.mf=null;state.fac=null;
      state.bld=null;state.bldReturn=null;
      // the mirrored destination is not the user's transfer pick - don't save it
      await api.post('/api/settings',{last_source:v,last_dest:state.xferDst||v});return loadSource();}
    if(v===state.dst){state.dst=state.xferDst=state.src;dstSel.value=state.dst;state.destData=null;}
    state.src=v;srcSel.value=v;state.cfg={};
    await api.post('/api/settings',{last_source:state.src,last_dest:state.dst});
    loadSource();};
  dstSel.onchange=async e=>{
    const v=e.target.value;
    if(v!==state.dst)activity('picked mod',`destination: ${v} (was ${state.dst})`);
    const srcChanged=(v===state.src);
    if(srcChanged){state.src=state.dst;srcSel.value=state.src;clearSelection();}
    state.dst=state.xferDst=v;dstSel.value=v;state.destData=null;state.destSnd=null;state.cfg={};
    await api.post('/api/settings',{last_source:state.src,last_dest:state.dst});
    if(srcChanged)loadSource();};
  // Strings filters on the SERVER (its biggest archive is 20 757 rows), so its
  // search is a debounced fetch rather than a repaint of what is already here.
  search.oninput=()=>{
    if(state.mode==='strings')return strSearch();
    render();};
  mercOnly.onchange=filtersChanged; groupBy.onchange=filtersChanged;
  // rebuilds the faction list (its A→Z changes) but keeps whatever is ticked
  facSort.onchange=()=>{state.settings.faction_sort=facSort.value;
    api.post('/api/settings',{faction_sort:facSort.value});
    if(state.data)buildFilter('factionFilter',state.data.factions,'faction',true);
    render();};
  document.querySelectorAll('.era').forEach(cb=>cb.onchange=()=>{cb.checked?state.sel.era.add(cb.value):state.sel.era.delete(cb.value);filtersChanged();});
  settingsBtn.onclick=openSettings;
  // …but not `logBtn.onclick=openLog`: a handler is called WITH the click,
  // and openLog's first argument is the mode to filter by. That filter
  // matched nothing, so the header's own button opened an empty log.
  logBtn.onclick=()=>openLog();
  selBtn.onclick=toggleSelMode; batchBtn.onclick=openBatch; clearSelBtn.onclick=clearSelection;
  packBtn.onclick=()=>packExport([...state.selected]); importPackBtn.onclick=packImport;
  cleanBtn.onclick=()=>cleanupFor(state.mode)(); unusedOnly.onchange=render;
  ownBtn.onclick=()=>openOwnership('units'); allFacBtn.onclick=()=>openOwnership('all');
  sndBtn.onclick=sndApply;
  backBldBtn.onclick=backToBuilding;
  /* Click the backdrop to close - but only a click that BEGAN on the backdrop.

     A `click` is dispatched on the nearest ancestor the mousedown and the mouseup
     still share, so if anything replaces the markup under the pointer between
     the two halves of one press, the click lands on #overlay and the dialog
     shuts. Several dialogs here re-render on `input` and on `change`, which
     makes that a real sequence: press inside a box, the box is rebuilt under the
     finger, release - and the window the user was typing in disappears. Whether
     it happens at all depends on how long the re-render takes, which is why it
     shows up on one machine and not another.

     Remembering where the press started costs one field and closes the hole:
     a click whose mousedown was inside the dialog is not a click on the
     backdrop, whatever the DOM did in between. */
  let overlayDown=false;
  overlay.addEventListener('mousedown',e=>{overlayDown=(e.target.id==='overlay');});
  overlay.onclick=e=>{if(e.target.id==='overlay'&&overlayDown)closeModal();};
  uiBackWire();
  rszInit();
}
/* ---------- mode switching ---------- */
// Edit and bmdb modes work on ONE mod in place, so the destination always mirrors
// the source: that also lets the "new unit" flow reuse the transfer engine with
// source == dest.
function applyMode(persist){
  syncNav();
  const one=state.mode!=='transfer', edit=state.mode==='edit', bm=state.mode==='bmdb',
        snd=state.mode==='sounds', spr=state.mode==='sprites', bld=state.mode==='buildings',
        str=state.mode==='strings', trt=state.mode==='traits',
        anc=state.mode==='ancillaries', mnr=state.mode==='minor',
        fac=state.mode==='factions',
        home=state.mode==='home';
  // Home is the one screen that is ABOUT the mods, so it does not sit under a
  // mod picker: every card carries its own.
  document.getElementById('srcLbl').style.display=home?'none':'';
  srcSel.style.display=home?'none':'';
  document.getElementById('srcLbl').textContent=one?'Mod':'From';
  document.getElementById('dstWrap').style.display=(one||home)?'none':'';
  // The map has nothing to search until 16g brings the query engine, and an
  // input that does nothing is worse than no input.
  search.style.display=(home||state.mode==='campmap')?'none':'';
  selBtn.style.display=one?'none':'';
  batchBtn.style.display=(!one&&state.selMode)?'inline-block':'none';
  clearSelBtn.style.display=(!one&&state.selMode&&state.selected.size)?'inline-block':'none';
  // A pack is made from the SOURCE mod and imported into the destination, so
  // both live in transfer mode - which is also the only mode where "the other
  // mod" is a thing at all.
  packBtn.style.display=(!one&&state.selMode&&state.selected.size)?'inline-block':'none';
  importPackBtn.style.display=one?'none':'inline-block';
  newUnitBtn.style.display=edit?'inline-block':'none';
  tidyEduBtn.style.display=edit?'inline-block':'none';
  const stm=state.mode==='stratmap', crd=state.mode==='cards',
        cmp=state.mode==='campmap';
  cleanBtn.style.display=(bm||stm)?'inline-block':'none';
  // the two faction-record fixers are about the modeldb itself, so they belong
  // to the Model entries tab and nowhere else
  ownBtn.style.display=allFacBtn.style.display=bm?'inline-block':'none';
  if(bm||stm)cleanBtn.textContent=bm?'🧹 Clean up BMDB…':'🧹 Clean up strat map…';
  sndBtn.style.display=snd?'inline-block':'none';
  unusedWrap.style.display=(bm||stm)?'inline-flex':'none';
  mercOnly.parentElement.style.display=
    (bm||snd||spr||bld||str||trt||anc||mnr||fac||home||stm||crd||cmp)?'none':'inline-flex';
  // these bring their own filters - the sidebar's faction/era ones say nothing
  // about a voice entry, and nothing at all about a modeldb record or a sprite
  document.getElementById('unitFilters').style.display=
    (bm||snd||spr||bld||str||trt||anc||mnr||fac||home||stm||crd||cmp)?'none':'';
  document.getElementById('bldFilters').style.display=bld?'':'none';
  // Only offered while the unit editor is what you'd be going back FROM: in
  // buildings mode the building is already on screen.
  backBldBtn.style.display=(edit&&state.bldReturn)?'inline-block':'none';
  if(state.bldReturn)backBldBtn.textContent=`← Back to ${state.bldReturn.label}`;
  search.placeholder=bm?'Search entries…':stm?'Search strat models…'
                    :crd?'Search units and cards…'
                    :snd?'Search units…':spr?'Search models…'
                    :bld?'Search buildings…':str?'Search tags and text…'
                    :trt?'Search traits…'
                    :anc?'Search ancillaries and types…'
                    :mnr?'Search this file…'
                    :fac?'Search factions…':'Search…';
  document.title=modeDef(state.mode).name+' · Medieval 2 GUI Toolkit';
  if(one&&state.selMode)toggleSelMode();
  // A single-mod mode mirrors the destination onto the source, but the pick the
  // user made in Transfer is remembered rather than overwritten - both in
  // `xferDst` and in the persisted setting, so neither this switch nor the next
  // run turns the transfer pair into A -> A. Transfer never shows A -> A anyway
  // (that is what Edit's "new unit from this one" is for), so coming back to it
  // with nothing to restore falls through to any other mod, same as a first run.
  if(one){
    if(state.dst!==state.src){state.xferDst=state.dst;
      state.dst=state.src;dstSel.value=state.src;state.destData=null;}
  }else if(state.dst===state.src&&state.mods.length>1){
    const want=state.xferDst&&state.xferDst!==state.src
      &&state.mods.some(m=>m.name===state.xferDst)
        ? state.xferDst : state.mods.find(m=>m.name!==state.src).name;
    state.dst=state.xferDst=want;dstSel.value=want;state.destData=null;state.destSnd=null;
  }
  if(persist)api.post('/api/settings',
    {mode:state.mode,last_dest:one?(state.xferDst||state.dst):state.dst});
  render();
}

// Leaving select mode keeps WHAT was ticked - you step out to look at a unit in
// the drawer, or to change a filter, and coming back to an empty pile after
// ticking twenty units was the worst way to lose work here. Only the highlight
// goes (a ticked card outside select mode just looks broken); ✕ Clear, switching
// source mod, and a finished transfer are what actually empty it.
function toggleSelMode(){state.selMode=!state.selMode;document.body.classList.toggle('selmode',state.selMode);
  selBtn.classList.toggle('on',state.selMode);
  paintSelection();
  batchBtn.style.display=state.selMode?'inline-block':'none';
  updateBatchBtn();}
function clearSelection(){state.selected.clear();paintSelection();updateBatchBtn();}
// every card of every selected unit, since one unit can render under several groups
function paintSelection(){main.querySelectorAll('.card').forEach(c=>
  c.classList.toggle('sel',state.selMode&&state.selected.has(c.dataset.type)));}
function updateBatchBtn(){batchBtn.textContent=`Transfer selected (${state.selected.size})`;batchBtn.disabled=state.selected.size===0;
  const on=state.selMode&&state.selected.size?'inline-block':'none';
  clearSelBtn.style.display=on;
  packBtn.style.display=state.mode==='transfer'?on:'none';
  packBtn.textContent=`📦 Export pack (${state.selected.size})`;}

function unitMatches(u){
  const qq=search.value.trim().toLowerCase();
  if(qq&&!(u.name.toLowerCase().includes(qq)||u.type.toLowerCase().includes(qq)||u.dictionary.toLowerCase().includes(qq)))return false;
  if(mercOnly.checked&&!u.mercenary)return false;
  const S=state.sel;
  if(S.faction.size&&!u.ownership.some(f=>S.faction.has(f)))return false;
  if(S.category.size&&!S.category.has(u.kind))return false;
  if(S.class.size&&!S.class.has(u.class))return false;
  if(S.era.size&&![...S.era].some(e=>(u.eras[e]||[]).length>0))return false;
  return true;
}
/* Every workspace is loaded asynchronously and the mode picker does not wait for
   it, so a read that takes a while - a 6000-entry modeldb, a whole voice bank,
   the first units load of a big mod - can come back after you have already moved
   on. Whoever started a load has to check it is still the one on screen before
   painting, or the new mode ends up wearing the old workspace's content (the
   toolbar and title switch, the body does not). `renderBuildings` has always
   done this; `stale()` is that same check for the rest. */
function stale(mode,mod){return state.mode!==mode||(mod!==undefined&&mod!==state.src);}
function render(){
  if(state.mode==='home')return renderHome();
  if(state.mode==='bmdb')return renderBmdb();
  if(state.mode==='sounds')return renderSounds();
  if(state.mode==='sprites')return renderSprites();
  if(state.mode==='stratmap')return state.stm?renderStratmap():loadStratmap();
  if(state.mode==='cards')return state.cards?renderCards():loadCards();
  if(state.mode==='campmap')return state.cmap?renderCampmap():loadCampmap();
  if(state.mode==='buildings')return renderBuildings();
  if(state.mode==='strings')return state.str?renderStrings():loadStrings();
  if(state.mode==='traits')return state.tr?renderTraits():loadTraits();
  if(state.mode==='ancillaries')return state.an?renderAncillaries():loadAncillaries();
  if(state.mode==='minor')return state.mf?renderMinor():loadMinor();
  if(state.mode==='factions')return state.fac?renderFactions():loadFactions();
  // the unit list is still loading, or its load failed - which are different
  // things and must not look the same, or a mod that cannot be read presents as
  // one that is taking a long time
  if(!state.data){
    const f=state.loadError;
    main.innerHTML=(f&&f.mod===state.src)?unitListFailedHtml(f.mod,f.why)
      :'<div class="empty">Loading '+esc(state.src)+'…</div>';
    return;}
  const units=state.data.units.filter(unitMatches);
  count.textContent=`${units.length}/${state.data.units.length}`;
  const gb=groupBy.value;
  if(!units.length){main.innerHTML='<div class="empty">No units match.</div>';return;}
  // Ticking a filter says "this is what I'm here for", so its group leads -
  // otherwise picking one faction buries it under every OTHER faction its units
  // are also owned by (a unit renders once per faction it belongs to). Alphabetical
  // within the picked ones, then alphabetical for the rest.
  const picked=state.sel[{faction:'faction',kind:'category',class:'class',era:'era'}[gb]]||new Set();
  const byPicked=(ka,kb,la,lb)=>(picked.has(kb)-picked.has(ka))||la.localeCompare(lb);
  let groups;
  if(gb==='none')groups=[['All units',units]];
  else if(gb==='faction'){const map=new Map();for(const u of units){for(const f of (u.ownership.length?u.ownership:['(none)']))(map.get(f)||map.set(f,[]).get(f)).push(u);}
    groups=[...map.entries()].sort((a,b)=>byPicked(a[0],b[0],facLabel(a[0]),facLabel(b[0]))).map(([f,us])=>[facLabel(f),us]);}
  // An era is a list of factions per era slot, so a unit lands in every era it
  // is fielded in - the same one-card-per-group rule faction grouping follows.
  else if(gb==='era'){const map=new Map();
    for(const u of units){const in_=ERA_KEYS.filter(e=>(u.eras[e]||[]).length);
      for(const e of (in_.length?in_:['-']))(map.get(e)||map.set(e,[]).get(e)).push(u);}
    groups=ERA_KEYS.concat('-').filter(e=>map.has(e)).map(e=>[ERA_LABEL[e],map.get(e)]);}
  else{const map=new Map();for(const u of units){const k=u[gb]||'(none)';(map.get(k)||map.set(k,[]).get(k)).push(u);}
    groups=[...map.entries()].sort((a,b)=>byPicked(a[0],b[0],a[0],b[0]));}
  main.innerHTML=groups.map(([g,us])=>{
    const key=gb+':'+g,off=state.folded.has(key);
    return `<section class="faction-group${off?' folded':''}">
    <div class="faction-head" onclick="toggleGroup('${q1(esc(key))}')"
      title="${off?'Show these units again':'Fold this group away'}">
      <span class="fold">${off?'▸':'▾'}</span>
      <h2>${esc(g)}</h2><span class="n">${us.length} units</span></div>
    ${off?'':`<div class="grid">${us.map(cardHtml).join('')}</div>`}</section>`;}).join('');
  main.querySelectorAll('.card').forEach(c=>c.onclick=()=>onCard(c.dataset.type));
}
// Custom-battle era slots, in the order the EDU writes them.
const ERA_KEYS=['0','1','2'];
const ERA_LABEL={'0':'Early','1':'High','2':'Late','-':'No era (campaign only)'};
/* Which group headings are folded shut. Keyed by group-by AND heading, so
   folding half the factions away does not also fold something in the category
   view, and remembered on the user's settings so it survives a reload the way
   the rest of the filter panel does. */
function toggleGroup(key){
  if(state.folded.has(key))state.folded.delete(key); else state.folded.add(key);
  state.settings.folded_groups=[...state.folded];
  api.post('/api/settings',{folded_groups:state.settings.folded_groups});
  render();
}
function cardHtml(u){
  const s=(state.selMode&&state.selected.has(u.type))?'sel':'';
  return `<div class="card ${s}" data-type="${esc(u.type)}">
    <div class="tick">✓</div>
    <img loading="lazy" onerror="iconRetry(this)" src="${iconUrl(state.src,u.type)}" alt="">
    <div class="meta"><div class="nm">${esc(u.name)}</div><div class="sub">${esc(u.type)}</div>
    <div>${u.eop?`<span class="badge eop" title="M2TWEOP unit, defined in ${esc(u.eop_file||'an EOP unit file')} rather than in export_descr_unit.txt">EOP</span>`:''}${u.mercenary?'<span class="badge merc">merc</span>':''}<span class="badge">${esc(u.kind||u.category||'?')}</span>${u.class?`<span class="badge cls">${esc(u.class)}</span>`:''}</div></div></div>`;
}
function onCard(type){
  if(state.selMode){ if(state.selected.has(type))state.selected.delete(type); else state.selected.add(type);
    updateBatchBtn(); markCardSel(type); return; }
  if(state.mode==='edit') return openEditor(type);
  openDrawer(type);
}
// A unit owned by several factions renders one card per faction group (and the
// same goes for the other group-by modes), so EVERY copy has to reflect the
// selection - querySelector would only ever find the first, making a selected
// unit look unselected under its other factions.
function markCardSel(type){const on=state.selMode&&state.selected.has(type);
  main.querySelectorAll(`.card[data-type="${cssq(type)}"]`).forEach(c=>c.classList.toggle('sel',on));}
const cssq=s=>s.replace(/"/g,'\\"');

function openDrawer(type){
  const u=state.data.units.find(x=>x.type===type); if(!u)return;
  const d=document.getElementById('drawer');
  const eras=['0','1','2'].filter(e=>(u.eras[e]||[]).length).map(e=>({0:'Early',1:'High',2:'Late'}[e])).join(', ')||'none';
  d.innerHTML=`<button class="close" onclick="drawer.classList.remove('open')">×</button>
    <div class="dh"><img onerror="iconRetry(this)" src="${iconUrl(state.src,u.type)}"><div><h2>${esc(u.name)}</h2><div class="sub">${esc(u.type)}</div></div></div>
    ${u.has_info?`<div class="infowrap"><div class="k">Info card</div><img onerror="this.parentElement.style.display='none'" src="${iconUrl(state.src,u.type,'info')}"></div>`:''}
    <div class="body">
      ${row('Dictionary',esc(u.dictionary))}
      ${row('Ownership',u.ownership.map(f=>`<span class="chip">${esc(facLabel(f))}</span>`).join('')||'none')}
      ${row('Category / Class',esc(u.kind||u.category||'none')+' / '+esc(u.class||'none'))}
      ${row('Eras',eras)}
      ${row('Battle models',u.models.map(m=>`<span class="chip">${esc(m)}</span>`).join('')||'none')}
      ${row('Officers / Mount',(u.officers.map(o=>`<span class="chip">${esc(o)}</span>`).join('')||'none')+(u.mount?`  mount: <span class="chip">${esc(u.mount)}</span>`:''))}
      ${(u.engine||u.mounted_engine)?row('Siege engine',`<span class="chip">${esc(u.engine||u.mounted_engine)}</span>${u.mounted_engine&&!u.engine?' <span class="count">(mounted)</span>':''}${(u.engine_groups||[]).length?`<span class="count"> · groups: ${(u.engine_groups||[]).map(esc).join(', ')}</span>`:''}`):''}
      <button class="primary" style="width:100%;margin-top:6px" onclick="drawer.classList.remove('open');openComposer(['${q1(esc(u.type))}'])">Transfer to “${esc(state.dst)}” →</button>
    </div>`;
  d.classList.add('open');
}
const row=(k,v)=>`<div class="row"><div class="k">${k}</div><div class="v">${v}</div></div>`;

/* ---------- credits ---------- */
async function openCredits(){
  let ver='';
  try{const p=await api.get('/api/ping');if(p.version)ver='v'+p.version;}catch(e){}
  const m=document.getElementById('modal');
  m.className='modal';
  m.innerHTML=`
    <div class="ehead"><div>
      <div class="nm" style="font-size:17px;color:var(--accent)">Medieval 2 GUI Toolkit</div>
      <div class="count">${esc(ver)}</div>
    </div></div>
    <div style="padding:16px;line-height:1.7">
      <div style="margin-bottom:14px">
        <div class="lbl" style="margin-bottom:4px">Developed by</div>
        <b>ProJYeet</b>
      </div>
      <div style="margin-bottom:14px">
        <div class="lbl" style="margin-bottom:4px">Co-developed by</div>
        <b>Demir</b>
      </div>
      <div style="margin-bottom:14px">
        <div class="lbl" style="margin-bottom:4px">Built on the work of, and
          thanking them for permission to take reference from their code</div>
        <div>Mylae’s
          <a href="https://github.com/Machiavello-1441/m2tw-editor" target="_blank"
             style="color:var(--accent2)">M2TW Editor</a></div>
        <div><a href="https://www.twcenter.net/ubs/medieval-2-total-war-modding-tool.26/"
             target="_blank" style="color:var(--accent2)">Fynn’s Medieval II Total
             War Modding Tool</a></div>
        <div>Bare Geomod, by <b>Sinople</b> and <b>Gigantus</b> -
          <a href="https://www.moddb.com/mods/bare-geomod-and-tools" target="_blank"
             style="color:var(--accent2)">moddb.com/mods/bare-geomod-and-tools</a></div>
        <div>TWMapReader, by <b>Withwnar</b> -
          <a href="https://www.twcenter.net/threads/tw-map-reader-v2-24-1-jul-2015-update.438278/"
             target="_blank" style="color:var(--accent2)">twcenter.net</a></div>
      </div>
      <div style="margin-bottom:14px">
        <div class="lbl" style="margin-bottom:4px">Sponsored by</div>
        <b>FeatherLeaf</b>
      </div>
      <div style="margin-bottom:14px">
        <div class="lbl" style="margin-bottom:4px">Special thanks</div>
        <b>Gigantus</b> and the <b>TWCenter</b> community, for the guides that
        taught everyone, this tool included, how these files actually work.
      </div>
      <div>
        <div class="lbl" style="margin-bottom:4px">Testing</div>
        <b>Jayzinski</b>, <b>TheHolyPilgrim</b>, <b>Espartan</b>, <b>Anhlego</b> and <b>Lupinemaverick</b>
      </div>
    </div>
    <div style="padding:0 16px 16px;text-align:right">
      <button class="primary" onclick="closeModal()">Close</button>
    </div>`;
  overlay.classList.add('open');
}
function closeModal(){
  // "…and did they save it?" is half of what makes a log readable
  if(overlay.classList.contains('open')&&undo.past.length)
    activity('closed dialog',`with ${undo.past.length} unsaved change(s)`);
  overlay.classList.remove('open');
  // Closing out of a sub-dialog abandons its stashed scroll: leaving it pending
  // would hand a dead snapshot to whatever re-draws next.
  usePlace(null);
  // the unit editor's 3D column is held outside the modal's markup so it can
  // survive a re-render (see edPrevAttach) - which means closing the dialog has
  // to hand it back rather than leaving a WebGL context and a draw loop running
  // for a dialog that is gone
  if(typeof edPrevDrop==='function')edPrevDrop();
  // …and the transfer composer's, which is the same column over a different dialog
  if(typeof cmpPrevDrop==='function')cmpPrevDrop();
  // the unit editor widens the modal - put it back for the next dialog
  document.getElementById('modal').className='modal';}

/* ---------- the browser's Back button ----------

   The whole toolkit is one page. A module, a dialog over it, sometimes a second
   panel stacked on the first - none of that is a browser page, so Back used to
   leave the tool outright, usually to the blank tab the launcher opened it in.
   It now steps back through the screens the tool actually has, and so do the
   mouse's own back button and Alt+←, which the browser sends down the same wire.

   There is no recorded history of screens to replay, and there deliberately
   isn't: every layer already knows how to close itself, and its on-screen
   Back / Cancel / ✕ is the call that does it. A press therefore asks the layers,
   innermost first, "are you what is on top?" - and the first one that says yes
   goes back exactly as its own button would, including whatever that button
   stops to ask first. A press and a click can never become two different ways
   out of one screen.

   One spare history entry is what makes a press reach us at all: it sits ahead
   of the page, each press spends it, and a press we answered puts it back. A
   press nothing answers is Home with nothing open - the tool's own root - and
   there the spare is left spent, so a second press leaves the page the way it
   always did. The next thing the user clicks arms it again. */

//: false = the spare has been spent and not replaced.
let uiBackArmed=false;
function uiBackArm(){
  if(uiBackArmed)return;
  // A page served over file:// (or a browser refusing the entry) must not take
  // the rest of the UI down with it - Back simply keeps its old behaviour there.
  try{ history.pushState({m2gt:'step'},''); uiBackArmed=true; }catch(e){}
}
/* The screens a press steps back through, innermost first.

   The three inside a dialog are the panels a dialog can stack on top of itself.
   Each keeps its OWN snapshot of the markup it covered up - that is what tells
   the layer it is the one on top, and it is the same field its Back button
   hands back. */
const NAV_LAYERS=[
  {on:()=>navMenu.classList.contains('open'), back:()=>navOpen(false)},
  {on:()=>drawer.classList.contains('open'), back:()=>drawer.classList.remove('open')},
  {on:()=>modalOpen()&&!!mpBack, back:()=>mpCancel()},
  {on:()=>modalOpen()&&!!imgBack, back:()=>imgCancel()},
  {on:()=>modalOpen()&&!!(state.bld&&state.bld.clause), back:()=>bldClauseCancel()},
  {on:()=>modalOpen()&&!!(state.bld&&(state.bld.cmp||state.bld.vc||state.bld.stash)),
   back:()=>bldPickCancel()},
  {on:()=>modalOpen(), back:()=>closeModal()},
  // Out of the dialogs: a unit editor reached FROM a building goes back to the
  // building, which is the trip the header's own ← button makes.
  {on:()=>state.mode==='edit'&&!!state.bldReturn, back:()=>backToBuilding()},
  // …and then the modules, in the order they were opened.
  {on:()=>state.modeTrail.length>0, back:()=>setAppMode(state.modeTrail.pop(),true)},
];
/* Step back one screen. Returns whether anything did.

   A layer whose module never loaded (a dropped <script> is a real thing here -
   see uiFailedFiles) would throw on the name that is not there, and taking the
   Back button down with it would be a poor way to report it. Such a layer is
   simply not open. */
function uiBack(){
  const layer=NAV_LAYERS.find(l=>{try{return l.on();}catch(e){return false;}});
  if(!layer)return false;
  layer.back();
  return true;
}
function uiBackWire(){
  uiBackArm();
  window.addEventListener('popstate',()=>{
    uiBackArmed=false;                   // the spare has just been spent
    if(uiBack())uiBackArm();
  });
  // Re-arming on a click keeps the arming in one place instead of in every
  // screen: a screen you can go back FROM is one you clicked your way into.
  // Capture, so a handler that stops the event still arms the way out of what
  // it just opened.
  document.addEventListener('click',()=>uiBackArm(),true);
}
