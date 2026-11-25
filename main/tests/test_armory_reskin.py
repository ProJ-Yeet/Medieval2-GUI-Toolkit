"""Rigging a part again shows on the animated model.

``armAnimGeo`` in ``web/js/armanim.js`` keeps each object's skinned geometry
and rebuilds it only when the object changes. The key held the LENGTH of the
weights, so rigging a sword from bone_rhand to bone_lhand (or a new share, or
Transfer weights after a rig) gave data of the same length and the old skin
stayed on screen: "Rig to bones did nothing". This runs armAnimGeo under node
with the page stubbed, rigs twice, and checks the second rig is what is drawn.

    python -m tests.test_armory_reskin
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

SRC = ROOT / "web" / "js" / "armanim.js"
ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


STUBS = r"""
const ANIM={geos:new Map()};
const armAnim=()=>ANIM;
const armObjMatrix=()=>[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
const armPivot=()=>[0,0,0];
const armAnimFree=()=>{};
const ARM={assets:new Map([['k',{geo:{positions:new Float32Array(9),normals:null,uvs:null,
  weights:new Float32Array([1,0,1,0,1,0]),joints:new Uint8Array(6),bones:['bone_Rhand'],
  groups:[{start:0,count:3}],indices:[0,1,2]}}]])};
function armPieceEach(live,pc,fn){ for(const v of live.geo.indices) fn(v); }
const armGl=()=>({ARRAY_BUFFER:1,ELEMENT_ARRAY_BUFFER:2,STATIC_DRAW:3,DYNAMIC_DRAW:4,
  createBuffer:()=>({}),bindBuffer:()=>{},bufferData:()=>{}});
const rig=bone=>{const w=new Float32Array([1,0,1,0,1,0]);const raw=new Uint8Array(24+12);
  raw.set(new Uint8Array(w.buffer),0);
  return {n:3,bones:[bone],mode:'rig',data:Buffer.from(raw).toString('base64')};};
global.atob=s=>Buffer.from(s,'base64').toString('binary');
"""

HARNESS = r"""
const o={id:1,src:[{asset:'k',group:0}],t:[0,0,0],r:[0,0,0],s:[1,1,1],weights:null};
const g0=armAnimGeo(o);
o.weights=rig('bone_rhand'); const g1=armAnimGeo(o);
o.weights=rig('bone_lhand'); const g2=armAnimGeo(o);
const g3=armAnimGeo(o);
console.log(JSON.stringify({b0:g0.bones,b1:g1.bones,b2:g2.bones,kept:g3===g2}));
"""

print("\n-- a part rigged again is skinned again (node) --")
node = shutil.which("node")
if not node:
    print("  [skip] node is not on PATH")
else:
    src = _webtext.read(SRC)
    m = re.search(r"^function armAnimGeo\(o\)\{.*?^\}", src, re.S | re.M)
    check("armanim.js has armAnimGeo", m)
    if m:
        tmp = Path(_tmp.mkdtemp(prefix="ut_reskin_"))
        js = tmp / "check.js"
        js.write_text(STUBS + m.group(0) + HARNESS, encoding="utf-8")
        proc = subprocess.run([node, str(js)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            check("armAnimGeo runs under node", False)
            print(proc.stderr[-1500:])
        else:
            r = json.loads(proc.stdout.strip().splitlines()[-1])
            check(f"the source's bone before any rig ({r['b0']})", r["b0"] == ["bone_Rhand"])
            check(f"the first rig is drawn ({r['b1']})", r["b1"] == ["bone_rhand"])
            check(f"rigged again, same size of data: the new bone is drawn ({r['b2']})", r["b2"] == ["bone_lhand"])
            check("unchanged weights keep the built geometry", r["kept"])

print()
print(f"{sum(ok)}/{len(ok)} checks - " + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
