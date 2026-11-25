"""A request nothing answered is asked again, and then the user is given Retry.

Switching menus fast used to leave a panel saying "Failed to fetch": during a
burst the server can refuse a connection that it answers two milliseconds
later (campmap.js measured it). ``fetchRetrying`` in ``web/js/core.js`` wraps
every fetch in the page, so each one is asked again a few times; only when the
tries are spent does it call the give-up hook, which shows the Retry bar.
An abandoned request (AbortError, an aborted signal) and a keepalive beacon are
never asked again and never show the bar.

This runs the wrapper under node against a fake fetch.

    python -m tests.test_fetch_retry
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


HARNESS = r"""
const out=[];
const say=(what,got,want)=>out.push({what,got,want,ok:JSON.stringify(got)===JSON.stringify(want)});
const dropped=()=>{const e=new TypeError('Failed to fetch');return e;};
const aborted=()=>{const e=new Error('aborted');e.name='AbortError';return e;};
function fake(plan){           // plan: one entry per call, 'ok' or a function making an error
  const f=async()=>{f.calls++;const p=plan[Math.min(f.calls-1,plan.length-1)];
    if(p==='ok')return {ok:true};throw p();};
  f.calls=0;return f;}
(async()=>{
  let gaveUp=0;const give=()=>{gaveUp++;};

  let f=fake([dropped,dropped,'ok']);
  let r=await fetchRetrying(f,give)('/api/x');
  say('two dropped requests, then an answer: the answer comes back',[r.ok,f.calls,gaveUp],[true,3,0]);

  f=fake([dropped]);let err=null;
  try{await fetchRetrying(f,give)('/api/x');}catch(e){err=e;}
  say('always dropped: tried 1 + every wait, then the Retry bar, once',
      [f.calls,gaveUp,!!(err&&err.retried)],[FETCH_WAIT.length+1,1,true]);

  gaveUp=0;f=fake([aborted]);err=null;
  try{await fetchRetrying(f,give)('/api/x');}catch(e){err=e;}
  say('an abandoned request is not asked again and shows no bar',
      [f.calls,gaveUp,err&&err.name],[1,0,'AbortError']);

  const ac={signal:{aborted:false}};f=fake([()=>{ac.signal.aborted=true;return dropped();}]);err=null;
  try{await fetchRetrying(f,give)('/api/x',{signal:ac.signal});}catch(e){err=e;}
  say('a request abandoned while it failed is not asked again',[f.calls,gaveUp],[1,0]);

  f=fake([dropped]);err=null;
  try{await fetchRetrying(f,give)('/api/heartbeat',{method:'POST',keepalive:true});}catch(e){err=e;}
  say('a keepalive beacon is not asked again and shows no bar',[f.calls,gaveUp,!!err],[1,0,true]);

  console.log(JSON.stringify(out));
})();
"""

print("\n-- a dropped request is asked again (node) --")
node = shutil.which("node")
if not node:
    print("  [skip] node is not on PATH")
else:
    src = _webtext.read(CORE)
    m = re.search(r"^const FETCH_WAIT=.*?(?=^window\.fetch=)", src, re.S | re.M)
    check("core.js has the fetch wrapper", m)
    if m:
        block = re.sub(r"^const FETCH_WAIT=\[[^\]]*\]", "const FETCH_WAIT=[1,1,1,1]", m.group(0), flags=re.M)
        tmp = Path(_tmp.mkdtemp(prefix="ut_fetchretry_"))
        js = tmp / "check.js"
        js.write_text(block + HARNESS, encoding="utf-8")
        proc = subprocess.run([node, str(js)], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            check("the wrapper runs under node", False)
            print(proc.stderr[-1800:])
        else:
            for s in json.loads(proc.stdout.strip().splitlines()[-1]):
                check(s["what"] + ("" if s["ok"] else f"  (got {s['got']!r}, want {s['want']!r})"), s["ok"])
    check("every fetch in the page goes through it",
          re.search(r"^window\.fetch=window\.fetch&&fetchRetrying\(", src, re.M))

print()
print(f"{sum(ok)}/{len(ok)} checks - " + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
