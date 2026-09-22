"""The browser's Back button, stepping back through the toolkit's own screens.

The whole tool is one page, so Back used to leave it. It now walks out the way
the user walked in - and the walk is decided entirely in the page, by
``NAV_LAYERS`` in ``web/js/core.js``: an ordered list of "is this what is on top?"
against "then this is how it closes". Two things about that are easy to get
quietly wrong, and neither would fail loudly in a browser:

  * **the order.** The layers are asked innermost first. Get one pair the wrong
    way round and a press shuts the whole dialog instead of the picker stacked on
    top of it, throwing away what the dialog was holding.
  * **a module that never loaded.** A dropped ``<script>`` is a real failure here
    (``uiFailedFiles`` exists because of it), and a layer that names a function
    from the missing file must not take the Back button down with it.

Then the trail of modules underneath: it records where Back goes, must not
record the trip Back itself makes, and must run out at Home - where a press is
let through, because leaving is the only thing left for it to mean.

This runs ``web/js/*.js`` under node with a hand-built page around it. Each
layer's ``back`` is a call that ships already (``mpCancel``, ``bldPickCancel``,
``closeModal`` …), so what is checked here is which of them a press reaches.

Run it with:

    python -m tests.test_back_button
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import _tmp

WEB = ROOT / "web" / "index.html"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


STUBS = r"""
const noop=()=>{};
const el=()=>{const on=new Set();return{
  classList:{add:c=>on.add(c),remove:c=>on.delete(c),toggle:(c,v)=>{v?on.add(c):on.delete(c);},
             contains:c=>on.has(c)},
  style:{},dataset:{},innerHTML:'',textContent:'',value:'',
  setAttribute:noop,addEventListener:noop,appendChild:noop,
  querySelector:()=>null,querySelectorAll:()=>[]};};
const ELS={};
const byId=id=>(ELS[id]||(ELS[id]=el()));
globalThis.document={addEventListener:noop,getElementById:byId,
  querySelector:()=>null,querySelectorAll:()=>[],createElement:el,body:{appendChild:noop}};
const WIRED={};
globalThis.window={addEventListener:(k,f)=>{WIRED[k]=f;},innerWidth:1280,innerHeight:800};
let PUSHES=0;
globalThis.history={pushState:()=>{PUSHES++;},back:noop,replaceState:noop};
globalThis.fetch=()=>Promise.reject(new Error('no network'));
// The ids the page reaches for as bare globals, the way a browser hands them over.
globalThis.navMenu=byId('navMenu');
globalThis.navBack=byId('navBack');
globalThis.drawer=byId('drawer');
globalThis.overlay=byId('overlay');
globalThis.main=byId('main');
"""

HARNESS = r"""
const out={say:[]};
const say=(what,got,want)=>out.say.push({what,got,want,ok:JSON.stringify(got)===JSON.stringify(want)});

// Every layer's way back is a call this editor already shipped; which of them a
// press REACHES is what the list decides, so each is swapped for a recorder.
let fired=[];
// only when it actually SHUTS an open menu: setAppMode calls navOpen(false) on
// every switch, and a recorder that counted those would read as a menu closing
// on screens where none was ever open
navOpen=open=>{if(!open&&navMenu.classList.contains('open'))fired.push('menu');
               navMenu.classList.toggle('open',open);};
mpCancel=()=>{fired.push('model picker');mpBack=null;};
imgCancel=()=>{fired.push('image picker');imgBack=null;};
bldClauseCancel=()=>{fired.push('clause');state.bld.clause=null;};
bldPickCancel=()=>{fired.push('sub-panel');state.bld.cmp=state.bld.vc=state.bld.stash=null;};
closeModal=()=>{fired.push('dialog');overlay.classList.remove('open');};
backToBuilding=()=>{fired.push('building');state.bldReturn=null;state.mode='buildings';};
applyMode=noop; activity=noop; render=noop; syncNav=noop; toast=noop;
// A route with a record in it waits for that screen's list to arrive before it
// picks the record. There is no screen and no list here, so the wait would be
// eighty timers deep and prove nothing; what is under test is the trail.
navWhen=noop;

function press(){fired=[];const did=uiBack();return {did,fired:fired.slice()};}
function shut(){
  navMenu.classList.remove('open'); drawer.classList.remove('open');
  overlay.classList.remove('open');
  mpBack=null; imgBack=null;
  state.bld=null; state.bldReturn=null; state.trail={list:[],i:-1}; state.mode='home';
}

// ---- the order: innermost first ---------------------------------------------
{
  // everything open at once, and then one press at a time all the way out
  shut();
  navMenu.classList.add('open');
  drawer.classList.add('open');
  overlay.classList.add('open');
  state.bld={clause:{},cmp:null,vc:{},stash:null};
  mpBack={}; imgBack={};
  const order=[];
  // the drawer closes itself in one line rather than through a named call, so
  // there is nothing to record: it is the press that fired nothing else.
  for(let i=0;i<8;i++){const p=press(); if(!p.did)break; order.push(p.fired[0]||'drawer');}
  say('a press takes the innermost screen first, one at a time',order,
      ['menu','drawer','model picker','image picker','clause','sub-panel','dialog']);
  say('…and the drawer went before any of the dialog',
      drawer.classList.contains('open'),false);
}
{
  shut();
  overlay.classList.add('open');
  state.bld={clause:null,cmp:null,vc:{},stash:null};
  say('a panel stacked in a dialog closes the PANEL, not the dialog',
      press().fired,['sub-panel']);
  say('…and the dialog is still open',overlay.classList.contains('open'),true);
}
{
  shut();
  overlay.classList.add('open');
  say('a plain dialog closes',press().fired,['dialog']);
}
{
  shut();
  state.mode='edit'; state.bldReturn={line:'barracks',lvl:0,label:'Barracks'};
  say('the unit editor reached from a building goes back to the building',
      press().fired,['building']);
}
{
  // a dialog is over the unit editor: the dialog goes first, the trip after
  shut();
  overlay.classList.add('open');
  state.mode='edit'; state.bldReturn={line:'barracks',lvl:0,label:'Barracks'};
  say('a dialog over that editor is shut before the trip is made',
      press().fired,['dialog']);
  say('…and the next press makes it',press().fired,['building']);
}

// ---- a module that never arrived ---------------------------------------------
{
  shut();
  overlay.classList.add('open');
  // exactly what a dropped <script> looks like from here: the name is not there
  NAV_LAYERS.unshift({on:()=>notAFunctionAnywhere(),back:()=>fired.push('ghost')});
  const p=press();
  NAV_LAYERS.shift();
  say('a layer whose module never loaded is simply not open',p.fired,['dialog']);
  say('…and the press still worked',p.did,true);
}

// ---- the trail: a list with a finger, not a stack ------------------------------
const modes=()=>state.trail.list.map(e=>e.route.mode);
{
  shut();
  navPush({mode:'home'});
  setAppMode('buildings'); setAppMode('traits');
  say('the trail records every place, not the places left behind',
      [modes(),state.trail.i],[['home','buildings','traits'],2]);
  press();
  say('a press walks the finger back one',[state.mode,state.trail.i],['buildings',1]);
  say('…and keeps what is ahead of it, which is what Forward walks',
      [modes(),navCan(1)],[['home','buildings','traits'],true]);
  navStep(1);
  say('forward goes back up it',[state.mode,state.trail.i],['traits',2]);
  press(); press();
  say('and out to where it started',[state.mode,state.trail.i],['home',0]);
  say('…where there is nothing behind and everything ahead',
      [navCan(-1),navCan(1)],[false,true]);
}
{
  // a browser drops the forward half when you set off somewhere new, and so
  // does this: the way you did not go is not a place you have been
  shut();
  navPush({mode:'home'});
  setAppMode('buildings'); setAppMode('traits');
  press(); press();
  setAppMode('bmdb');
  say('a new move from part way back drops what was ahead',
      [modes(),navCan(1)],[['home','bmdb'],false]);
}
{
  shut();
  navPush({mode:'home'});
  navGo({mode:'buildings',name:'hinterland_castles'});
  const e=state.trail.list[state.trail.i];
  say('a route carries its record into the trail, and into the crumb',
      [e.route.mode,e.route.name,e.label],
      ['buildings','hinterland_castles','Buildings · hinterland_castles']);
  say('…and the setAppMode inside it did not file a second, thinner crumb',
      state.trail.list.length,2);
}
{
  // a dialog over the screen you are leaving does not come with you: it is shut
  // the same way its own ✕ shuts it, before the screen underneath changes
  shut();
  navPush({mode:'buildings'});
  overlay.classList.add('open');
  fired=[];
  setAppMode('health');
  say('a mode switch shuts what was stacked on the screen it left',
      [fired,overlay.classList.contains('open')],[['dialog'],false]);
  shut();
  navPush({mode:'buildings'});
  overlay.classList.add('open');
  state.bld={clause:{},cmp:null,vc:null,stash:null};
  fired=[];
  navGo({mode:'health'});
  say('…innermost first, exactly as a Back press would',fired,['clause','dialog']);
}
{
  shut();
  say('at Home with nothing open and nowhere behind, nothing answers',press().did,false);
}
{
  shut();
  navPush({mode:'home'});
  const many=['buildings','traits','bmdb','sounds','strings','factions'];
  for(let i=0;i<40;i++)setAppMode(many[i%many.length]);
  say('the trail is capped rather than grown for a whole session',
      state.trail.list.length<=24,true);
  say('…and the finger is still on the end of it',
      state.trail.i,state.trail.list.length-1);
}

// ---- the address of a place ----------------------------------------------------
{
  // the whole of "middle-click opens it in a new tab" rests on this being a real
  // URL that a fresh tab can be opened on and read back
  state.src='ROCSS';
  const r={mode:'campdb',name:'agents/assassinate_chance_max'};
  const url=navUrl(r);
  say('a route has an address, with the mod on it',
      url,'/?mod=ROCSS&go=campdb&name=agents%2Fassassinate_chance_max');
  const back=navFromQs(new URLSearchParams(url.slice(2)));
  say('…and the address reads back as the route',back,r);
  say('an empty route is Home, not a broken address',
      navFromQs(new URLSearchParams('mod=ROCSS')),{mode:'home'});
  // the `&` is written `&amp;` because it is inside an attribute; a browser
  // reads it back as `&`, which is the address the new tab actually opens
  const a=navLinkHtml({mode:'health'},'Open →','mini','go');
  say('a link is an anchor with a real href - nothing else makes middle click work',
      [a.startsWith('<a href="/?mod=ROCSS&amp;go=health"'),a.includes('data-nav=')],
      [true,true]);
}

// ---- the spare history entry ---------------------------------------------------
{
  shut();
  PUSHES=0; uiBackArmed=false;
  uiBackWire();
  say('wiring the page arms one spare entry',PUSHES,1);
  uiBackArm();
  say('arming again while armed pushes nothing',PUSHES,1);
  overlay.classList.add('open');
  fired=[]; WIRED.popstate();
  say('a press that closed something puts the spare back',[PUSHES,fired],[2,['dialog']]);
  fired=[]; WIRED.popstate();
  say('a press nothing answered leaves it spent - the next one leaves the page',
      PUSHES,2);
  uiBackArm();
  say('…and the next thing the user clicks arms it again',PUSHES,3);
}

console.log(JSON.stringify(out));
"""


print("\n-- the Back button's layers (node) --")
node = shutil.which("node")
if not node:
    print("  [skip] node is not on PATH - the page's own JS cannot be exercised")
elif not WEB.exists():
    print("  [skip] web/index.html not found")
else:
    src = WEB.read_text(encoding="utf-8")
    tags = [t for t in re.findall(r'<script src="js/([A-Za-z0-9_.-]+\.js)"></script>', src)
            if t != "boot.js"]          # boot.js starts the app; there is no server here
    script = "\n".join((WEB.parent / "js" / t).read_text(encoding="utf-8") for t in tags)
    tmp = Path(_tmp.mkdtemp(prefix="ut_back_"))
    js = tmp / "check.js"
    js.write_text(STUBS + script + HARNESS, encoding="utf-8")
    proc = subprocess.run([node, str(js)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        check("the page script runs under node", False)
        print(proc.stderr[-1800:])
    else:
        r = json.loads(proc.stdout.strip().splitlines()[-1])
        for s in r["say"]:
            check(s["what"] + ("" if s["ok"] else f"  (got {s['got']!r}, want {s['want']!r})"),
                  s["ok"])


print()
print(f"{sum(ok)}/{len(ok)} checks - "
      + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
