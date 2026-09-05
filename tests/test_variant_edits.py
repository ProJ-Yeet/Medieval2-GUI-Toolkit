"""Typing a recruit pool's numbers in the city/castle panel, and copying them across.

The panel that puts a building's two halves side by side used to be able to say
only that they disagreed. Now the four numbers on either side are boxes, and a
button under each side puts all four onto the other half. Nothing about that is a
server call - the panel edits the same working copy the building form behind it
is editing, and stages the twin's rows in ``work.also`` - so what can go quietly
wrong is *which row* an edit lands on:

  * a number typed on THIS half must rewrite the row already in the working copy,
    not add a second pool for the same unit;
  * a number typed on the TWIN must be staged against the EDB line that row
    already occupies, so the server rewrites it where it stands. Two numbers
    typed one after the other must land on ONE staged row, not two;
  * a row this panel mirrored a moment ago has no line in the file yet, and must
    not inherit the *other* building's line number - that would point a later
    edit of the same boxes at a line in the wrong building.

So this suite runs the page's own functions under node against a hand-built
panel, and then checks the one thing the server had to start sending for any of
it to work: the EDB line of each side's pool, on every city/castle pair of every
installed mod.

Run it with:

    python -m tests.test_variant_edits
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
from unittransfer.buildings import variant_compare, variant_pairs
from unittransfer.mod import Mod

MODS = Path(r"C:/Users/projy/Downloads/Games/Total War MEDIEVAL II Definitive Edition/mods")
WEB = ROOT / "web" / "index.html"

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


def installed_mods():
    if not MODS.is_dir():
        return []
    return [Mod(p) for p in sorted(MODS.iterdir())
            if (p / "data" / "export_descr_buildings.txt").exists()]


STUBS = r"""
const noop=()=>{};
globalThis.document={addEventListener:noop,getElementById:()=>null,
  querySelector:()=>null,querySelectorAll:()=>[],
  createElement:()=>({style:{},classList:{add:noop}}),body:{appendChild:noop}};
globalThis.window={addEventListener:noop,innerWidth:1280,innerHeight:800};
globalThis.fetch=()=>Promise.reject(new Error('no network'));
"""

HARNESS = r"""
const out={say:[],html:{}};
// The panel repaints its own markup and shouts in a toast; neither is what this
// is about, and both want a document. The staging underneath them is the whole
// point, so it is the real thing.
bldVarRender=()=>{};
bldVarRepaint=(li,lv,u)=>{bldVarDiff(u);};
const toasts=[];
toast=m=>{toasts.push(m);};
activity=noop;

const say=(what,got,want)=>out.say.push({what,got,want,ok:JSON.stringify(got)===JSON.stringify(want)});

const POOL=(unit,n,line,faction)=>({unit,initial:n[0],per_turn:n[1],maximum:n[2],
  experience:n[3],requires:n[4]||'',cap_line:line===undefined?null:line,
  faction:!!faction});

function panel(units){
  state.src='M';
  state.data={units:[],factions:[]};      // bldAddPoolRow looks a mirrored unit up here
  state.bld={mod:'M',line:'barracks',lvl:0,culture:'',
    d:{levels:[{label:'Wooden wall'}],units:{}},
    work:{levels:[{name:'wooden_wall',caps:[
      {line:100,keyword:'recruit_pool',args:'',requires:'',conds:[],condEdited:false,
       bonus:false,value:'',pool:POOL('spearmen',['1','0.5','2','0']),comment:'',
       faction:false,del:false}],fcaps:[]}],also:{}},
    vc:{only:'all',r:{
      line:'barracks',settlement:'city',twin:'castle_barracks',twin_settlement:'castle',
      only_a:0,only_b:0,differs:0,
      levels:[{level:'wooden_wall',level_index:0,twin_level:'motte_and_bailey',
               units,only_a:0,only_b:0,differs:0}]}}};
  const lv=state.bld.vc.r.levels[0];
  lv.only_a=units.filter(u=>u.where==='a').length;
  lv.only_b=units.filter(u=>u.where==='b').length;
  lv.differs=units.filter(u=>u.numbers_differ).length;
  const r=state.bld.vc.r;
  r.only_a=lv.only_a; r.only_b=lv.only_b; r.differs=lv.differs;
  return state.bld;
}
const both=()=>({unit:'spearmen',name:'Spearmen',where:'both',missing:false,
  a:POOL('spearmen',['1','0.5','2','0','factions { england, }'],100,false),
  b:POOL('spearmen',['2','0.5','4','0','factions { scotland, }'],250,true),
  diff:['initial','maximum','requires'],numbers_differ:true,same:false});
const staged=()=>((state.bld.work.also['castle_barracks']||{})['motte_and_bailey']||[]);
const here=()=>state.bld.work.levels[0].caps.filter(c=>c.pool&&!c.del);

// ---- 1) a number typed on THIS half -----------------------------------------
{
  panel([both()]);
  bldVarSet(0,'spearmen','a','initial','7');
  say('this half: the row already in the working copy is rewritten',
      here().map(c=>c.pool.initial),['7']);
  say('this half: no second pool for the same unit', here().length,1);
  say('this half: nothing is staged against the twin', staged().length,0);
}

// ---- 2) a number typed on the TWIN ------------------------------------------
{
  panel([both()]);
  bldVarSet(0,'spearmen','b','maximum','9');
  say('twin: one row staged under the twin line and its facing tier', staged().length,1);
  say('twin: staged against the EDB line that row occupies', staged()[0].line,250);
  say('twin: it is a recruit_pool', staged()[0].keyword,'recruit_pool');
  say('twin: the clause the file already holds goes back untouched',
      [staged()[0].requires,staged()[0].condEdited],['factions { scotland, }',false]);
  say('twin: a faction_capability row stays one', staged()[0].faction,true);
  say('twin: the typed number is on it', staged()[0].pool.maximum,'9');
  say('twin: this half is left alone', here()[0].pool.maximum,'2');
  bldVarSet(0,'spearmen','b','initial','5');
  say('twin: a second number lands on the SAME staged row', staged().length,1);
  say('twin: …carrying both', [staged()[0].pool.initial,staged()[0].pool.maximum],['5','9']);
}

// ---- 3) Copy: all four across, in the direction the button says --------------
{
  const u=panel([both()]).vc.r.levels[0].units[0];
  bldVarCopy(0,'spearmen','a');
  say('copy city to castle: the castle half now has the city half\u2019s four',
      [u.b.initial,u.b.per_turn,u.b.maximum,u.b.experience],
      [u.a.initial,u.a.per_turn,u.a.maximum,u.a.experience]);
  say('copy city to castle: staged in place against the castle row', staged()[0].line,250);
  say('copy city to castle: and the numbers reached it',
      [staged()[0].pool.initial,staged()[0].pool.maximum],['1','2']);
  say('copy city to castle: the city half is untouched', here()[0].pool.initial,'1');
  say('the row now reads as in step', u.numbers_differ,false);
  say('…but the clauses are still counted as different', u.diff,['requires']);
}
{
  const u=panel([both()]).vc.r.levels[0].units[0];
  bldVarCopy(0,'spearmen','b');
  say('copy castle to city: the working copy takes the castle half\u2019s numbers',
      [here()[0].pool.initial,here()[0].pool.maximum],['2','4']);
  say('copy castle to city: nothing is staged for the twin', staged().length,0);
}
{
  const u=panel([both()]).vc.r.levels[0].units[0];
  u.b=JSON.parse(JSON.stringify(u.a)); u.b.cap_line=250; u.b.faction=true;
  bldVarCopy(0,'spearmen','a');
  say('copying four numbers that already match stages nothing', staged().length,0);
  say('…and says so', toasts.length>0&&/already trains/.test(toasts[toasts.length-1]),true);
}

// ---- 4) a row this panel mirrored a moment ago -------------------------------
{
  // the city half trains it, the castle half does not: ⇄ Mirror, then type
  panel([{unit:'archers',name:'Archers',where:'a',missing:false,
          a:POOL('archers',['1','0.5','2','0','factions { england, }'],100,false),
          b:null,diff:[],numbers_differ:false,same:false}]);
  state.bld.work.levels[0].caps=[];        // this half's own rows are beside the point
  bldVarMirrorOne(0,'archers');
  say('mirror into the twin stages one row', staged().length,1);
  say('a row that is not in the file yet carries no line', staged()[0].line,null);
  bldVarSet(0,'archers','b','maximum','6');
  say('typing on it updates that row rather than adding another', staged().length,1);
  say('…and it still carries no line - it is not the city half\u2019s',
      [staged()[0].line,staged()[0].pool.maximum],[null,'6']);
}
{
  // the castle half trains it, the city half does not: mirrored INTO this line
  panel([{unit:'archers',name:'Archers',where:'b',missing:false,a:null,
          b:POOL('archers',['3','0.5','6','1','factions { scotland, }'],250,true),
          diff:[],numbers_differ:false,same:false}]);
  const was=here().length;
  bldVarMirrorOne(0,'archers');
  say('mirror into this half adds one pool to the working copy', here().length,was+1);
  bldVarSet(0,'archers','a','initial','4');
  say('typing on it edits that pool rather than adding another', here().length,was+1);
  say('…and the number is on it',
      here().filter(c=>c.pool.unit==='archers')[0].pool.initial,'4');
}

// ---- 5) what counts as a difference -----------------------------------------
{
  const u=both();
  u.a.initial=u.b.initial; u.a.maximum=u.b.maximum;
  bldVarDiff(u);
  say('a clause that differs is not a difference in the numbers',
      [u.numbers_differ,u.diff],[false,['requires']]);
  u.b.experience='4';
  bldVarDiff(u);
  say('one of the four that differs is', [u.numbers_differ,u.diff],
      [true,['experience','requires']]);
}

// ---- 6) the markup the row actually renders ----------------------------------
{
  panel([both()]);
  const row=bldVarRowHtml(state.bld.vc.r.levels[0].units[0],0);
  out.html.both={
    boxes:(row.match(/data-vc="/g)||[]).length,
    sides:(row.match(/data-vcside="(a|b)"/g)||[]).length,
    copies:(row.match(/class="vccopy"/g)||[]).length,
    toCastle:row.indexOf('Copy city \u2192 castle')>=0,
    toCity:row.indexOf('Copy castle \u2192 city')>=0,
  };
  panel([{unit:'archers',name:'Archers',where:'a',missing:false,
          a:POOL('archers',['1','0.5','2','0'],100,false),b:null,
          diff:[],numbers_differ:false,same:false}]);
  const gap=bldVarRowHtml(state.bld.vc.r.levels[0].units[0],0);
  out.html.gap={
    boxes:(gap.match(/data-vc="/g)||[]).length,
    copies:(gap.match(/class="vccopy"/g)||[]).length,
    notTrained:gap.indexOf('not trained')>=0,
    mirror:gap.indexOf('Mirror')>=0,
  };
}

console.log(JSON.stringify(out));
"""


print("\n-- the city/castle panel's boxes (node) --")
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
    tmp = Path(_tmp.mkdtemp(prefix="ut_vc_"))
    js = tmp / "check.js"
    js.write_text(STUBS + script + HARNESS, encoding="utf-8")
    proc = subprocess.run([node, str(js)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        check("the page script runs under node", False)
        print(proc.stderr[-1500:])
    else:
        r = json.loads(proc.stdout.strip().splitlines()[-1])
        for s in r["say"]:
            check(s["what"] + ("" if s["ok"] else f"  (got {s['got']!r}, want {s['want']!r})"),
                  s["ok"])
        print("\n  -- and what the row renders --")
        b = r["html"]["both"]
        check("a row both halves train has eight boxes, four a side", b["boxes"] == 8)
        check("…tagged with the side they belong to", b["sides"] == 8)
        check("…and a copy button on each side", b["copies"] == 2)
        check("the city side's button says where its numbers would go", b["toCastle"])
        check("…and the castle side's says the same the other way", b["toCity"])
        g = r["html"]["gap"]
        check("a unit only one half trains shows four boxes, not eight", g["boxes"] == 4)
        check("…no copy button, because there is nothing to overwrite", g["copies"] == 0)
        check("…the empty half says so", g["notTrained"])
        check("…and closing the gap is still the Mirror button", g["mirror"])


print("\n-- every side of every pair names the line its pool sits on --")
mods = installed_mods()
if not mods:
    print("  [skip] no mod installed")
for mod in mods:
    pairs = variant_pairs(mod.edb)
    if not pairs:
        check(f"{mod.name}: has a city/castle pair to compare", False)
        continue
    seen = tried = bad_line = bad_faction = missing = 0
    # A pair reported both ways round is the same comparison twice; one of each
    # is enough, and a big mod has hundreds.
    done = set()
    for line in sorted(pairs):
        if pairs[line] in done:
            continue
        done.add(line)
        tried += 1
        if tried > 12:
            break
        view = variant_compare(mod, line, "")
        for lv in view["levels"]:
            for u in lv["units"]:
                for side, name in (("a", view["line"]), ("b", view["twin"])):
                    p = u[side]
                    if p is None:
                        continue
                    seen += 1
                    if "cap_line" not in p or "faction" not in p:
                        missing += 1
                        continue
                    if not isinstance(p["faction"], bool):
                        bad_faction += 1
                    text = mod.edb.lines[p["cap_line"]] if 0 <= p["cap_line"] < len(mod.edb.lines) else ""
                    if "recruit_pool" not in text or f'"{p["unit"]}"' not in text:
                        bad_line += 1
    check(f"{mod.name}: {seen} pool(s) across {min(tried, 12)} pair(s) carry both keys",
          seen and not missing)
    check(f"{mod.name}: every cap_line is the recruit_pool line for that unit",
          not bad_line)
    check(f"{mod.name}: every faction flag is a bool", not bad_faction)


print()
print(f"{sum(ok)}/{len(ok)} checks - "
      + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
