"""A script that broke because an earlier one was dropped: the page loads again.

When ``armory.js`` is dropped at load, ``armtex.js`` runs next and throws
"ARM is not defined" at its first line. Fetching armory.js again (core.js's
``retryDroppedUiFiles``) cannot mend armtex.js: running it a second time would
throw on its own ``const`` names, which the first run left half made. So a
load where a later script threw after a drop reloads the page, once; a second
time it says which file would not load. A script that throws with nothing
dropped before it is a fault in that script and still shows the bug bar.

This runs core.js's loading block under node with the page stubbed.

    python -m tests.test_ui_dropped_script
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _webtext  # noqa: E402
from tests import _tmp  # noqa: E402

CORE = ROOT / "web" / "js" / "core.js"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


RUN = r"""
const out={};
function page(store){
  const L=[];
  const window={addEventListener:(t,f,cap)=>L.push({t,f})};
  const T={reloads:0,inited:0,barHidden:false,main:{innerHTML:''}};
  const ctx={window,L,T,
    document:{querySelectorAll:()=>['core','armory','armtex','boot'].map(n=>({src:`http://x/js/${n}.js?v=1`})),
              head:{appendChild:s=>setTimeout(()=>s.onload(),0)},createElement:()=>({})},
    sessionStorage:{getItem:k=>store[k]||null,setItem:(k,v)=>{store[k]=String(v);},removeItem:k=>{delete store[k];}},
    location:{reload:()=>{T.reloads++;}},
    main:T.main, tt:(k,p)=>k+':'+((p&&p.names)||''), esc:s=>s,
    wireKeepPlace:()=>{}, init:()=>{T.inited++;}};
  return ctx;
}
function load(store, events){
  const c=page(store);
  const f=new Function(...Object.keys(c), BLOCK+'\nreturn {startUi};');
  const api=f(...Object.values(c));
  // the app's own bug bar: a later, bubbling listener on window
  c.L.push({t:'error',f:e=>{ if(e.message) c.T.barShown=true; }});
  for(const ev of events){
    let stopped=false;
    const e=Object.assign({stopImmediatePropagation:()=>{stopped=true;}},ev);
    for(const l of c.L.filter(l=>l.t==='error')){ if(stopped)break; l.f(e); }
  }
  return api.startUi().then(()=>c.T);
}
const drop=n=>({target:{tagName:'SCRIPT',src:`http://x/js/${n}.js?v=1`}});
const thrown=n=>({message:'Uncaught ReferenceError: ARM is not defined',filename:`http://x/js/${n}.js?v=1`,
  error:Object.assign(new Error('ARM is not defined'),{name:'ReferenceError'}),target:{}});
(async()=>{
  const store={};
  let t=await load(store,[drop('armory'),thrown('armtex')]);
  out.first={reloads:t.reloads,inited:t.inited,bar:!!t.barShown};
  t=await load(store,[drop('armory'),thrown('armtex')]);
  out.second={reloads:t.reloads,inited:t.inited,bar:!!t.barShown,said:t.main.innerHTML.includes('armtex.js')};
  t=await load(store,[]);
  out.clean={reloads:t.reloads,inited:t.inited,flag:store.uiReloaded||null};
  t=await load({}, [thrown('armtex')]);
  out.ownFault={reloads:t.reloads,inited:t.inited,bar:!!t.barShown};
  console.log(JSON.stringify(out));
})();
"""

print("\n-- a script broken by a dropped one (node) --")
node = shutil.which("node")
if not node:
    print("  [skip] node is not on PATH")
else:
    src = _webtext.read(CORE)
    m = re.search(r"^const uiFailedFiles=\[\];.*?^window\.addEventListener\('load',\(\)=>startUi\(\)\);",
                  src, re.S | re.M)
    check("core.js has its loading block", m)
    if m:
        tmp = Path(_tmp.mkdtemp(prefix="ut_dropjs_"))
        js = tmp / "check.js"
        js.write_text("const BLOCK=" + json.dumps(m.group(0)) + ";\n" + RUN, encoding="utf-8")
        proc = subprocess.run([node, str(js)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            check("the block runs under node", False)
            print(proc.stderr[-1500:])
        else:
            r = json.loads(proc.stdout.strip().splitlines()[-1])
            check(f"armory.js dropped, armtex.js threw: the page loads again, no bug bar ({r['first']})",
                  r["first"] == {"reloads": 1, "inited": 0, "bar": False})
            check(f"the same after that reload: it says armtex.js would not load, no loop ({r['second']})",
                  r["second"] == {"reloads": 0, "inited": 0, "bar": False, "said": True})
            check(f"a clean load starts the app and forgets the reload ({r['clean']})",
                  r["clean"] == {"reloads": 0, "inited": 1, "flag": None})
            check(f"a script's own fault, nothing dropped: the bug bar, the app starts ({r['ownFault']})",
                  r["ownFault"] == {"reloads": 0, "inited": 1, "bar": True})

print()
print(f"{sum(ok)}/{len(ok)} checks - " + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
